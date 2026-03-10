# 🚀 OpenSource Repo Grabber (OSRG)

**OpenSource Repo Grabber** is a powerful desktop application designed to monitor and explore the open-source ecosystem. It tracks top-starred and trending repositories on GitHub, providing detailed insights, version history, and AI-powered code explanations.

## 🌟 Project Oracle (AI Intelligence)
Recently upgraded with **Project Oracle**, featuring:
- **Deep Architectural Audits**: Full project analysis using multi-file context.
- **Smart Tagging**: AI-powered project categorization.
- **Analysis Agent**: Specialized `kimi-k2.5:cloud` integration for elite code explanation.
- **Earthy Glassmorphism**: A beautiful, inspired UI overhaul.

![OSRG Preview](https://via.placeholder.com/1200x800.png?text=OpenSource+Repo+Grabber+UI)

## ✨ Key Features

-   **Perpetual Scanning:** Background service that automatically updates repository data every 30 minutes (configurable).
-   **Curated Tracking:** Monitors the top 30 all-time starred and top 30 trending repositories with permissive licenses (MIT, Apache 2.0, BSD).
-   **Deep Insights:** View READMEs, release history, recent commits, and top contributors for every project.
-   **AI-Powered Explanations:** Integrated with **Ollama** to provide intelligent code explanations and project summaries.
-   **Local Storage:** All data is cached locally in a SQLite database for fast, offline access.
-   **Integrated Browser:** Browse repository pages directly within the application.
-   **Beautiful UI:** Modern dark-themed interface built with `customtkinter`.

## 🛠️ Technology Stack

-   **Backend:** Python 3.x
-   **GUI:** `customtkinter`
-   **Database:** SQLite
-   **AI Integration:** Ollama API
-   **External APIs:** GitHub REST API

## 📋 Prerequisites

-   **Python 3.8+**
-   **Ollama:** (Optional, for AI features) Ensure Ollama is installed and running locally.
-   **GitHub Token:** (Recommended) To avoid API rate limits, get a Personal Access Token (PAT) from GitHub.

## 🚀 Getting Started

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/yourusername/OpenSourceRepoGrabber.git
    cd OpenSourceRepoGrabber
    ```

2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Configuration:**
    Open `config.py` and add your GitHub token to avoid rate limits:
    ```python
    GITHUB_TOKEN = "your_github_token_here"
    ```

4.  **Run the application:**
    ```bash
    python run.py
    ```

## 🤖 AI Integration (Ollama)

To enable AI code explanations, ensure [Ollama](https://ollama.ai/) is installed and running. By default, the app looks for Ollama at `http://localhost:11434`.

Recommended models:
-   `llama3.2`
-   `qwen2.5`
-   `mistral`

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

*Made with ❤️ for the Open Source Community.*
