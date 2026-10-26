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
st.set_page_config(page_title="RepoGuide AI", page_icon="📚", layout="centered")

# Cinematic Theme CSS
st.markdown("""
    <style>
    .main {
        background-color: #0e1117;
    }
    .stTextArea textarea {
        background-color: #161b22 !important;
        color: #c9d1d9 !important;
        border: 1px solid #30363d !important;
        border-radius: 12px !important;
    }
    div.stButton > button {
        background-color: #21262d !important;
        color: #58a6ff !important;
        border: 1px solid #30363d !important;
        border-radius: 8px !important;
        transition: all 0.3s ease;
        width: 100%;
    }
    div.stButton > button:hover {
        border-color: #58a6ff !important;
        background-color: #30363d !important;
        box-shadow: 0 0 10px rgba(88, 166, 255, 0.2);
    }
    .stSelectbox label, .stTextArea label {
        color: #8b949e !important;
        font-weight: 500 !important;
    }
    .stMarkdown h1 {
        color: #f0f6fc !important;
        text-align: center !important;
    }
    .stMarkdown p {
        text-align: center !important;
        color: #8b949e !important;
    }
    .response-panel {
        background-color: #161b22;
        border: 1px solid #30363d;
        border-left: 4px solid #58a6ff;
        padding: 20px;
        border-radius: 12px;
        color: #c9d1d9;
        margin-top: 20px;
        width: 100%;
    }
    </style>
    """, unsafe_allow_html=True)

# Hero Section
st.markdown("# 📚 RepoGuide AI")
st.markdown("### Transform complex codebases into beginner-friendly guides")
st.markdown("<p style='text-align: center; font-size: 0.8rem; color: #58a6ff;'>Powered by Gemma 4 + Ollama | Local & Private</p>", unsafe_allow_html=True)
st.write("---")

# Model Selection
available_models = get_available_models()
if not available_models:
    st.warning("⚠️ No Ollama models detected. I'll try using 'gemma' by default, but please make sure you have a model pulled (e.g., `ollama pull gemma`).")
    selected_model = DEFAULT_MODEL
else:
    selected_model = st.selectbox("Select AI Model", available_models)

# Input Area
user_input = st.text_area("Paste your Code or README here:", height=300, placeholder="Paste code snippets or README.md content...", help="Input the code or documentation you want the AI to explain.")

# Action Buttons
col1, col2, col3 = st.columns(3)

with col1:
    if st.button("🚀 Explain Project"):
        if user_input.strip():
            with st.spinner("Analyzing..."):
                result = call_ollama("Explain this project in simple terms for a complete beginner. Focus on what it does and the main goal.", user_input, selected_model)
                st.markdown('<div class="response-panel">', unsafe_allow_html=True)
                st.markdown(result)
                st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.error("Please paste some content first!")

with col2:
    if st.button("💻 Explain Code"):
        if user_input.strip():
            with st.spinner("Decoding..."):
                result = call_ollama("Explain this code snippet step-by-step for a beginner. Tell me how it works and why certain parts are used.", user_input, selected_model)
                st.markdown('<div class="response-panel">', unsafe_allow_html=True)
                st.markdown(result)
                st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.error("Please paste some content first!")

with col3:
    if st.button("🏁 Where to Start?"):
        if user_input.strip():
            with st.spinner("Mapping..."):
                result = call_ollama("Looking at this content, if I were a beginner wanting to contribute or run this, where is the best place to start? What files or sections should I look at first?", user_input, selected_model)
                st.markdown('<div class="response-panel">', unsafe_allow_html=True)
                st.markdown(result)
                st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.error("Please paste some content first!")

st.write("---")
st.markdown("<p style='text-align: center; color: #484f58;'>Processing happens entirely on your local machine. Your data never leaves your computer.</p>", unsafe_allow_html=True)
