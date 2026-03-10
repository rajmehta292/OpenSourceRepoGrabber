# Project Oracle: High-Level Architecture

This document provides a technical deep-dive into the "Project Oracle" architecture, designed for professional-grade reliability, security, and scalability.

## 🏗️ System Overview
Project Oracle is an intelligent layer on top of the OpenSource Repo Grabber that transforms static repository data into actionable architectural insights.

### 🌓 Key Components
1. **RepoManager (The Context Engine)**:
   - Responsible for secure context extraction.
   - **Hardening**: Automatically excludes sensitive patterns (`.env`, `.pem`, etc.) and enforces a 1MB file size safety limit.
   - **Optimization**: Limits context windows to the top 200 files and 5KB content snippets to optimize LLM performance.

2. **OllamaClient (The AI Core)**:
   - Interfaces with `kimi-k2.5:cloud` or local Ollama models.
   - **Robustness**: Features a tiered exponential backoff retry strategy (3 attempts) for absolute reliability under transient network stress.
   - **Isolation**: All AI calls are stateless and encapsulated with clear error boundaries.

3. **Database (Persistent Intelligence)**:
   - Uses SQLite with an idempotent migration layer.
   - Stores AI-generated "Architectural Audits" and "Smart Tags" to minimize redundant API calls and provide instant user feedback.

4. **GUI (The Professional Interface)**:
   - **Aesthetics**: "Earthy Glassmorphism" system with 16px corner radii and sage/sand palettes.
   - **Professional Polish**: Integrated ToolTip system and non-blocking background threads for all I/O and AI operations.

## 🔄 Lifecycle of an Audit
1. **User Request**: User clicks "Audit" in the repository view.
2. **Context Mining**: `RepoManager` scans the local folder, builds a sanitized file tree, and extracts anchor file contents.
3. **Reasoning**: `OllamaClient` sends the 3-step structured prompt to the AI.
4. **Persistence**: Insights are mapped to the repository identity and persisted to SQLite.
5. **UI Update**: The GUI receives the completion signal via `.after()` and updates the view thread-safely.

---
*Built for absolute reliability and professional performance.*
