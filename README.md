# 📚 RepoGuide AI

RepoGuide AI is a beginner-friendly tool that helps new developers understand code snippets and project READMEs using local AI models.

## 🚀 Quick Start

### Prerequisites
1. **Ollama**: Install it from [ollama.com](https://ollama.com).
2. **Gemma Model**: Pull the model you want to use:
   ```bash
   ollama pull gemma
   ```

### Installation
1. Clone or navigate to this directory.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### Running the App
1. Ensure Ollama is running in the background.
2. Start the Streamlit app:
   ```bash
   streamlit run app.py
   ```

## 🛠️ How it works
RepoGuide AI connects to the local Ollama API. It sends your code or README along with a specific persona-driven prompt to Gemma, which then generates a beginner-friendly explanation.

## 🌟 Features
- **Project Overview**: Get a high-level summary of what a project does.
- **Code Breakdown**: Understand the logic of a snippet step-by-step.
- **Onboarding Guide**: Find the best starting point for contributing.
