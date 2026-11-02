"""A small, readable client for the Ollama HTTP API.

Only three things happen here:
  * ask Ollama which models are installed,
  * stream a chat completion token by token,
  * turn network weirdness into errors a human can act on.

No SDK, no framework - just `requests`. That keeps the dependency surface
small and makes it obvious what is being sent to the model.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Iterable, Iterator

import requests

from . import config


# --------------------------------------------------------------------------
# Errors
# --------------------------------------------------------------------------
class OllamaError(RuntimeError):
    """Base class for anything that goes wrong talking to Ollama."""


class OllamaUnavailable(OllamaError):
    """Ollama isn't running, or isn't reachable at the configured host."""


class ModelMissing(OllamaError):
    """The selected model hasn't been pulled yet."""


# --------------------------------------------------------------------------
# Model metadata
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class ModelInfo:
    name: str
    size_bytes: int = 0
    family: str = ""
    parameter_size: str = ""
    quantization: str = ""

    @property
    def size_gb(self) -> float:
        return self.size_bytes / (1024 ** 3)

    @property
    def label(self) -> str:
        """Human-readable one-liner, e.g. 'gemma:latest · 4B · 4.7 GB'."""
        bits = [self.name]
        if self.parameter_size:
            bits.append(self.parameter_size)
        if self.size_gb:
            bits.append(f"{self.size_gb:.1f} GB")
        return "  ·  ".join(bits)


# --------------------------------------------------------------------------
# Client
# --------------------------------------------------------------------------
class OllamaClient:
    def __init__(self, host: str | None = None) -> None:
        self.host = (host or config.OLLAMA_HOST).rstrip("/")

    # -- plumbing ---------------------------------------------------------
    def _url(self, path: str) -> str:
        return f"{self.host}{path}"

    def _connect_error(self, exc: Exception) -> OllamaUnavailable:
        return OllamaUnavailable(
            f"Could not reach Ollama at {self.host}. "
            "Start it with `ollama serve` (or open the Ollama app) and try again."
        )

    # -- health -----------------------------------------------------------
    def health(self) -> tuple[bool, str]:
        """Cheap liveness probe. Returns (is_up, message)."""
        try:
            r = requests.get(self._url("/api/version"), timeout=(3, 8))
            if r.status_code == 200:
                version = r.json().get("version", "unknown")
                return True, f"Ollama {version} at {self.host}"
            return False, f"Ollama responded with HTTP {r.status_code}."
        except requests.RequestException:
            return False, f"Nothing listening at {self.host}."

    # -- models -----------------------------------------------------------
    def list_models(self) -> list[ModelInfo]:
        try:
            r = requests.get(self._url("/api/tags"), timeout=(3, 12))
        except requests.RequestException as exc:
            raise self._connect_error(exc) from exc

        if r.status_code != 200:
            raise OllamaError(f"Ollama returned HTTP {r.status_code} when listing models.")

        models: list[ModelInfo] = []
        for raw in r.json().get("models", []):
            details = raw.get("details") or {}
            models.append(
                ModelInfo(
                    name=raw.get("name") or raw.get("model") or "",
                    size_bytes=int(raw.get("size") or 0),
                    family=details.get("family") or "",
                    parameter_size=details.get("parameter_size") or "",
                    quantization=details.get("quantization_level") or "",
                )
            )
        models.sort(key=lambda m: m.name)
        return [m for m in models if m.name]

    # -- chat -------------------------------------------------------------
    def chat_stream(
        self,
        model: str,
        messages: Iterable[dict],
        *,
        temperature: float = 0.3,
        num_ctx: int = config.DEFAULT_NUM_CTX,
    ) -> Iterator[str]:
        """Yield the reply as text chunks.

        Raising happens lazily, so wrap the *iteration* in try/except, not the
        call itself.
        """
        payload = {
            "model": model,
            "messages": list(messages),
            "stream": True,
            "keep_alive": config.KEEP_ALIVE,
            "options": {
                "temperature": temperature,
                "num_ctx": num_ctx,
            },
        }

        try:
            response = requests.post(
                self._url("/api/chat"),
                json=payload,
                stream=True,
                timeout=(10, config.READ_TIMEOUT),
            )
        except requests.ConnectionError as exc:
            raise self._connect_error(exc) from exc
        except requests.Timeout as exc:
            raise OllamaError("Ollama took too long to start responding.") from exc
        except requests.RequestException as exc:
            raise OllamaError(f"Request to Ollama failed: {exc}") from exc

        with response:
            if response.status_code == 404:
                raise ModelMissing(
                    f"Model '{model}' is not installed. Run: ollama pull {model}"
                )
            if response.status_code != 200:
                body = (response.text or "").strip()[:300]
                raise OllamaError(f"Ollama returned HTTP {response.status_code}: {body}")

            produced_anything = False
            for line in response.iter_lines(decode_unicode=True):
                if not line:
                    continue
                try:
                    chunk = json.loads(line)
                except json.JSONDecodeError:
                    continue  # tolerate keep-alive noise

                if error := chunk.get("error"):
                    raise OllamaError(str(error))

                piece = (chunk.get("message") or {}).get("content") or ""
                if piece:
                    produced_anything = True
                    yield piece

                if chunk.get("done"):
                    break

            if not produced_anything:
                raise OllamaError(
                    "The model returned an empty reply. Try a shorter input or a different model."
                )
