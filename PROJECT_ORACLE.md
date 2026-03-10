# Project Oracle: AI Architecture Agent

Project Oracle transforms the standard repository grabber into a context-aware **AI Project Architect**. It moves beyond simple file summaries to performing deep architectural audits across the entire project structure.

## 🚀 Core Features

### 1. Multi-File Context Extraction
Unlike standard AI assistants that look at one file at a time, Project Oracle uses `RepoManager.get_project_context` to:
- Generate a recursive **File Tree** (respecting `.gitignore` patterns).
- Identify **Anchor Files** (e.g., `package.json`, `requirements.txt`, `docker-compose.yml`).
- Capture high-signal file contents to build a mental map of the project's skeleton.

### 2. Deep Architectural Audit
Triggered via the **"Audit"** button in the repository list, this agent performs:
- **Pattern Identification**: Detects MVC, Layered, Microservices, etc.
- **Dependency Analytics**: Analyzes tech stacks and entry points.
- **Strategic Roadmap**: Suggestions for performance, scalability, and refactoring.

### 3. Smart Tagging
The AI automatically generates 3-5 high-relevance tags based on the README and file structure (e.g., `Event-Driven`, `Scalable-API`, `React-Frontend`). These tags are displayed on the main repository cards for quick visual classification.

## 🛠️ Technical Architecture

### Data Layer
- **Models**: `Repository` now includes `architectural_audit` (TEXT) and `smart_tags` (JSON-stored-as-TEXT).
- **Migration**: Automatic schema migration in `Database._migrate_db` ensures columns are added without data loss.

### AI Engine
- **Kimi-k2.5:cloud Integration**: Optimized for larger context windows, allowing it to "see" more of the project at once.
- **Structured Prompting**: Uses multi-step logical chain-of-thought to ensure architectural accuracy.

## 🧪 Verification
- **Internal Suite**: `tests_oracle.py` verifies context extraction and database persistence.
- **Robustness**: Implemented fallback lookup strategies for repository matching and thread-safe UI updates.

---
*Design Language: Earthy Glassmorphism (Jony Ive inspired)*
