"""Prompt design.

The quality of this tool lives almost entirely in this file. Each "mode" is a
persona plus a required output shape, so answers stay consistent and scannable
instead of drifting into walls of text.
"""

from __future__ import annotations

SYSTEM_PROMPT = """\
You are RepoGuide, a patient senior software engineer who explains code to \
first-year computer science students.

Rules you never break:
- Use plain language. Define any jargon the first time you use it, in brackets.
- Prefer concrete analogies over abstract description.
- Never invent files, functions, APIs, or behaviour that are not in the material \
you were given. If something is unclear or missing, say "this isn't shown in \
the provided code" instead of guessing.
- Be concise. Short paragraphs, bullet points, no filler and no flattery.
- Format with GitHub-flavoured Markdown. Use `inline code` for identifiers and \
fenced code blocks with a language tag when showing code.
- If the material looks like it was truncated, mention it once, briefly.
"""


# Each mode: id -> metadata used by the UI and by the prompt builder.
MODES: dict[str, dict] = {
    "project": {
        "label": "Project overview",
        "icon": "🧭",
        "help": "What is this project, and what problem does it solve?",
        "instruction": """\
Explain this project to someone who has never seen it before.

Structure your answer as:

## What this is
Two or three sentences. What does it do, in plain English?

## The problem it solves
Why would someone build this? What was annoying before it existed?

## How it works
Walk through the main flow from a user's action to the result. Name the key
files/parts and what each one is responsible for.

## Built with
The main technologies, and one line on why each is there.

## Worth knowing
Anything surprising, clever, or unfinished that a newcomer should be told.""",
    },
    "code": {
        "label": "Code walkthrough",
        "icon": "🔍",
        "help": "Line-by-line meaning of a snippet or file.",
        "instruction": """\
Explain this code to a beginner, stepping through it in the order it executes.

Structure your answer as:

## The big picture
One sentence: what does this code achieve overall?

## Step by step
Follow the actual execution order. For each meaningful block, say what it does
and *why* it's written that way. Quote only the lines that matter.

## Concepts used
List the language features or patterns that appear (with a one-line definition
each) - for example decorators, list comprehensions, context managers.

## Watch out for
Anything fragile, surprising, or a common beginner mistake in this code.

## Try it yourself
One small, safe change the reader could make to see what happens.""",
    },
    "start": {
        "label": "Where to start",
        "icon": "🏁",
        "help": "The shortest path from zero to running/contributing.",
        "instruction": """\
A beginner wants to run this project and then contribute. Give them a route.

Structure your answer as:

## Start here
The exact first file to open, and what to look for in it.

## Reading order
A numbered path through the codebase, cheapest-first. Explain why each step
comes before the next.

## Get it running
The setup steps implied by the files shown: dependencies, config, commands,
environment variables. Flag anything you cannot confirm from the material.

## Your first change
Two or three beginner-sized tasks that would genuinely help this project.

## Skip for now
Files or folders that look intimidating but don't matter yet.""",
    },
    "review": {
        "label": "Code review",
        "icon": "🛠️",
        "help": "Bugs, risks, and concrete improvements.",
        "instruction": """\
Review this code as a thoughtful senior engineer would in a pull request.

Structure your answer as:

## Overall
Two sentences: what's the quality level, and what's the single biggest issue?

## Bugs and risks
Ordered by severity. For each: what goes wrong, when, and how to fix it.
If you are not certain something is a bug, label it as a suspicion.

## Improvements
Concrete, small, and worth doing. Skip pure style nitpicks unless they hurt
readability.

## Security and secrets
Any credentials, injection risks, unvalidated input, or unsafe defaults. If
none are visible, say so plainly.

## Keep doing
Two things this code does well, so the author knows what to preserve.""",
    },
}


def build_analysis_messages(
    mode_id: str,
    context_text: str,
    *,
    included: int,
    dropped: int,
    truncated: bool,
) -> list[dict]:
    """Assemble the message list for the first analysis pass."""
    mode = MODES[mode_id]

    coverage = [f"{included} file(s) included in the material below."]
    if dropped:
        coverage.append(f"{dropped} file(s) were left out to fit the model's context window.")
    if truncated:
        coverage.append("At least one file was cut off partway through.")

    user_message = (
        f"{mode['instruction']}\n\n"
        f"---\n\n"
        f"### Material\n"
        f"({'; '.join(coverage)})\n\n"
        f"{context_text}"
    )

    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_message},
    ]


def build_followup_messages(history: list[dict], question: str) -> list[dict]:
    """Add a follow-up question to an existing conversation."""
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        *history,
        {"role": "user", "content": question},
    ]
