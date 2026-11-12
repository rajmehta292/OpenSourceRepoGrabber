# 🚀 OpenSource Repo Grabber (OSRG)

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![UI: CustomTkinter](https://img.shields.io/badge/UI-CustomTkinter-emerald.svg)](https://github.com/TomSchimansky/CustomTkinter)
[![AI: Project Oracle](https://img.shields.io/badge/AI-Project%20Oracle%20%2B%20Heuristic-green.svg)]()

**OpenSource Repo Grabber (OSRG)** is an advanced desktop command center designed to monitor, explore, audit, and contribute to the global open-source software ecosystem.

Whether you are a **tinkerer** looking to play with cool projects, a **software architect** auditing patterns and tech stacks, or an **aspiring open-source contributor** making your first pull request, OSRG gives you an unfair advantage.

---

## 🌟 Tailored for 3 Developer Journeys

```
                    ┌────────────────────────┐
                    │      OSRG Hub          │
                    └───────────┬────────────┘
         ┌──────────────────────┼──────────────────────┐
         ▼                      ▼                      ▼
  ⚡ The Tinkerer        🏗️ The Builder         🌱 The Contributor
 • Quick README modal    • Oracle Architecture   • Good First Issues
 • In-app File Tree      • Pattern Detection     • License Decoder
 • 1-Click Starter Pack  • Smart Editor Launch   • 5-Step PR Checklist
 • Code Explanation      • Git Sync & Auditing   • Git Cheat Sheet
```

### 1. ⚡ The Tinkerer & Explorer
- **Zero-Friction Previews**: Inspect full `README.md` contents and explore recursive file trees without needing to clone gigabytes of code.
- **Curated Starter Packs**: One-click import for iconic libraries (*FastAPI, Flask, Rich, uv, shadcn/ui*).
- **AI Code Spark**: Instantly explain any function, script, or component using Project Oracle or the built-in Heuristic engine.

### 2. 🏗️ The Deep Builder & Architect
- **Project Oracle Architecture Audits**: Multi-file context extraction detects architectural patterns (MVC, Layered, Microservices, Event-Driven), discovers tech stacks, evaluates technical debt, and synthesizes a strategic technical roadmap.
- **Smart Semantic Tagging**: AI and heuristic tags auto-classify projects (e.g. `FastAPI`, `Dockerized`, `Async-I/O`, `CI/CD-Ready`).
- **Seamless IDE Integration**: Launch projects directly into **Cursor**, **VS Code**, **Windsurf**, or system explorer.
- **License-Based Organization**: Local storage automatically files repositories into clean SPDX-compliant folders (`MIT`, `Apache-2.0`, `BSD-3-Clause`, etc.).

### 3. 🌱 The Open-Source Learner & Contributor
- **Good First Issues Launchpad**: Filter and search GitHub repositories actively seeking beginner contributions with `good-first-issue` and `help-wanted` tags.
- **Interactive License Decoder**: Plain-English guide to open-source licenses (MIT vs Apache 2.0 vs BSD vs GPL vs AGPL)—understand commercial rights, patent grants, and copyleft obligations with clarity.
- **First PR Checklist**: Step-by-step interactive workflow guiding you from forking and local branch setup to Conventional Commits and submitting pull requests.

---

## ✨ Key Features & Architecture

- **Welcome & Overview Hub**: First-time user experience featuring live project KPIs, system status indicators, quick action launchpads, and curated starter repositories.
- **Resilient Dual-Engine Intelligence**:
  - **Local Neural Engine (Ollama)**: Seamlessly connects to `llama3.2`, `qwen2.5`, `kimi-k2.5:cloud`, or `mistral`.
  - **Built-in Heuristic Architecture Engine**: Automatically analyzes directory structures, anchor configs (`package.json`, `pyproject.toml`, `Dockerfile`), and dependencies to generate architectural audits even when Ollama is offline.
- **Rate-Limit Resilience**: Gracefully handles GitHub unauthenticated API restrictions with smart caching and curated offline fallbacks.
- **Earthy Glassmorphism UI**: Beautiful, refined interface with dark/light themes inspired by minimalist industrial design.

---

## 🚀 Getting Started

### 1. Prerequisites
- **Python 3.8+** (Python 3.10–3.12 recommended)
- **Git** installed on your system
- **Ollama** (Optional, for neural AI features): [ollama.ai](https://ollama.ai)

### 2. Installation
```bash
# Clone the repository
git clone https://github.com/rajmehta292/OpenSourceRepoGrabber.git
cd OpenSourceRepoGrabber

# Create and activate virtual environment
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Run the Application
```bash
python run.py
```

### 4. Optional GitHub Token Setup
To increase your GitHub API rate limits from 60 to 5,000 requests/hour, set your Personal Access Token in environment variables or `config.py`:
```bash
set GITHUB_TOKEN=ghp_your_token_here
```

---

## 🧪 Running Test Suites

OSRG includes an automated verification suite:

```bash
# Run Oracle & context persistence tests
python tests_oracle.py

# Run Ollama resilience & retry tests
python tests_ollama.py

# Run enhancements, heuristic audit, and contributor suite tests
python tests_enhancements.py
```

---

## 📄 License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

*Made with ❤️ for the Global Open Source Community.*
