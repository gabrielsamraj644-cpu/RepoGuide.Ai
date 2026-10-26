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
st.set_page_config(page_title="RepoGuide AI", page_icon="📚", layout="wide")

# Professional Developer Theme CSS
st.markdown("""
    <style>
    /* Main App Background */
    .stApp {
        background-color: #0a0c10;
    }
    
    /* Center content and set max width for a professional feel */
    .block-container {
        max-width: 1000px !important;
        padding-top: 3rem !important;
    }

    /* Header Styling */
    .header-area {
        text-align: center;
        margin-bottom: 3rem;
    }
    .main-title {
        font-size: 3rem !important;
        font-weight: 800 !important;
        color: #f0f6fc !important;
        margin-bottom: 0.5rem !important;
        background: linear-gradient(90deg, #58a6ff, #bc8cff);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .tagline {
        font-size: 1.2rem !important;
        color: #8b949e !important;
        margin-bottom: 1rem !important;
    }
    .model-badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        background-color: #161b22;
        border: 1px solid #30363d;
        color: #58a6ff;
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 1px;
    }

    /* Input Panel Styling */
    .input-section {
        background-color: #0d1117;
        border: 1px solid #30363d;
        border-radius: 16px;
        padding: 2rem;
        margin-bottom: 2rem;
        box-shadow: 0 4px 20px rgba(0,0,0,0.3);
    }
    .section-heading {
        color: #c9d1d9 !important;
        font-size: 1.1rem !important;
        font-weight: 600 !important;
        margin-bottom: 1.5rem !important;
        display: flex;
        align-items: center;
        gap: 10px;
    }

    /* Input Widgets */
    .stTextArea textarea {
        background-color: #010409 !important;
        color: #c9d1d9 !important;
        border: 1px solid #30363d !important;
        border-radius: 8px !important;
        font-family: 'JetBrains Mono', 'Fira Code', monospace !important;
        font-size: 0.9rem !important;
    }
    .stSelectbox label, .stTextArea label {
        color: #8b949e !important;
        font-size: 0.9rem !important;
    }

    /* Action Buttons */
    div.stButton > button {
        background-color: #21262d !important;
        color: #f0f6fc !important;
        border: 1px solid #30363d !important;
        border-radius: 8px !important;
        padding: 0.6rem 1rem !important;
        font-weight: 500 !important;
        transition: all 0.2s ease;
        width: 100%;
    }
    div.stButton > button:hover {
        border-color: #58a6ff !important;
        background-color: #30363d !important;
        color: #58a6ff !important;
        box-shadow: 0 0 15px rgba(88, 166, 255, 0.15);
    }

    /* Analysis Section */
    .analysis-heading {
        color: #f0f6fc !important;
        font-size: 1.5rem !important;
        font-weight: 700 !important;
        margin-top: 3rem !important;
        margin-bottom: 1rem !important;
        border-bottom: 1px solid #30363d;
        padding-bottom: 0.5rem;
    }
    .response-container {
        background-color: #0d1117;
        border: 1px solid #30363d;
        border-left: 4px solid #58a6ff;
        border-radius: 12px;
        padding: 2rem;
        color: #c9d1d9;
        line-height: 1.7;
        width: 100%;
        box-shadow: 0 10px 30px rgba(0,0,0,0.5);
    }
    .response-container h1, .response-container h2, .response-container h3 {
        color: #f0f6fc !important;
        margin-top: 1.8rem !important;
        margin-bottom: 0.8rem !important;
    }
    .response-container p {
        margin-bottom: 1.2rem !important;
    }
    .response-container ul, .response-container ol {
        margin-bottom: 1.2rem !important;
        padding-left: 1.5rem !important;
    }
    .response-container li {
        margin-bottom: 0.5rem !important;
    }
    /* Style embedded code blocks in responses */
    .stMarkdown code {
        background-color: #161b22 !important;
        color: #ff7b72 !important;
        padding: 2px 6px !important;
        border-radius: 4px !important;
        border: 1px solid #30363d !important;
    }
    .stMarkdown pre {
        background-color: #010409 !important;
        border-radius: 8px !important;
        border: 1px solid #30363d !important;
        padding: 1rem !important;
    }
    
    /* Footer */
    .footer {
        text-align: center;
        padding: 3rem 0;
        color: #484f58;
        font-size: 0.8rem;
    }
    </style>
    """, unsafe_allow_html=True)

# Header Section
st.markdown('<div class="header-area">', unsafe_allow_html=True)
st.markdown('<h1 class="main-title">📚 RepoGuide AI</h1>', unsafe_allow_html=True)
st.markdown('<p class="tagline">Understand any codebase. One step at a time.</p>', unsafe_allow_html=True)
st.markdown('<div class="model-badge">Powered by Gemma 4 + Ollama</div>', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

# Workspace
st.markdown('<div class="input-section">', unsafe_allow_html=True)
st.markdown('<div class="section-heading">📂 Input Workspace</div>', unsafe_allow_html=True)

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
                st.session_state['ai_response'] = result
                st.session_state['response_type'] = 'Project'
        else:
            st.error("Please paste some content first!")

with col2:
    if st.button("💻 Explain Code"):
        if user_input.strip():
            with st.spinner("Decoding..."):
                result = call_ollama("Explain this code snippet step-by-step for a beginner. Tell me how it works and why certain parts are used.", user_input, selected_model)
                st.session_state['ai_response'] = result
                st.session_state['response_type'] = 'Code'
        else:
            st.error("Please paste some content first!")

with col3:
    if st.button("🏁 Where to Start?"):
        if user_input.strip():
            with st.spinner("Mapping..."):
                result = call_ollama("Looking at this content, if I were a beginner wanting to contribute or run this, where is the best place to start? What files or sections should I look at first?", user_input, selected_model)
                st.session_state['ai_response'] = result
                st.session_state['response_type'] = 'Starting Point'
        else:
            st.error("Please paste some content first!")
st.markdown('</div>', unsafe_allow_html=True)

# Results Section
if 'ai_response' in st.session_state:
    st.markdown('<div class="analysis-heading">✨ AI Analysis: ' + st.session_state['response_type'] + '</div>', unsafe_allow_html=True)
    st.markdown('<div class="response-container">', unsafe_allow_html=True)
    st.markdown(st.session_state['ai_response'])
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown('<div class="footer">Processing happens entirely on your local machine. Your data never leaves your computer.</div>', unsafe_allow_html=True)
