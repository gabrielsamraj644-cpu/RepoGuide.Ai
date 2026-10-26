import streamlit as st
import requests
import json

# Configuration
OLLAMA_URL = "http://localhost:11434/api/chat"
# We'll try to detect the model, but default to 'gemma' or 'gemma2'
DEFAULT_MODEL = "gemma" 

def get_available_models():
    try:
        response = requests.get("http://localhost:11434/api/tags")
        if response.status_code == 200:
            models = [m['name'] for m in response.json().get('models', [])]
            return models
    except Exception:
        return []
    return []

def call_ollama(prompt, content, model_name):
    full_prompt = f"{prompt}\n\nContent to analyze:\n{content}"
    payload = {
        "model": model_name,
        "messages": [{"role": "user", "content": full_prompt}],
        "stream": False
    }
    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=300)
        if response.status_code == 200:
            return response.json()['message']['content']
        else:
            return f"Error: Ollama API returned status code {response.status_code}"
    except requests.exceptions.ConnectionError:
        return "Error: Could not connect to Ollama. Please make sure Ollama is running locally on port 11434."
    except Exception as e:
        return f"An unexpected error occurred: {str(e)}"

# UI Setup
st.set_page_config(page_title="RepoGuide AI", page_icon="📚")

st.title("📚 RepoGuide AI")
st.markdown("""
Welcome to **RepoGuide AI**! I'm here to help beginners understand complex codebases and READMEs.
Paste your content below and choose what you want to know.
""")

# Model Selection
available_models = get_available_models()
if not available_models:
    st.warning("⚠️ No Ollama models detected. I'll try using 'gemma' by default, but please make sure you have a model pulled (e.g., `ollama pull gemma`).")
    selected_model = DEFAULT_MODEL
else:
    selected_model = st.selectbox("Select Model", available_models)

# Input Area
user_input = st.text_area("Paste your Code or README here:", height=300, placeholder="Paste code snippets or README.md content...")

# Action Buttons
col1, col2, col3 = st.columns(3)

with col1:
    if st.button("🚀 Explain this project"):
        if user_input.strip():
            with st.spinner("Analyzing project..."):
                result = call_ollama("Explain this project in simple terms for a complete beginner. Focus on what it does and the main goal.", user_input, selected_model)
                st.info(result)
        else:
            st.error("Please paste some content first!")

with col2:
    if st.button("💻 Explain this code"):
        if user_input.strip():
            with st.spinner("Decoding logic..."):
                result = call_ollama("Explain this code snippet step-by-step for a beginner. Tell me how it works and why certain parts are used.", user_input, selected_model)
                st.info(result)
        else:
            st.error("Please paste some content first!")

with col3:
    if st.button("🏁 Where should I start?"):
        if user_input.strip():
            with st.spinner("Finding the entry point..."):
                result = call_ollama("Looking at this content, if I were a beginner wanting to contribute or run this, where is the best place to start? What files or sections should I look at first?", user_input, selected_model)
                st.info(result)
        else:
            st.error("Please paste some content first!")

st.divider()
st.caption("Powered by Ollama & Gemma | Local & Private")
