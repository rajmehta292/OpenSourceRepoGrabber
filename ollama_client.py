"""
Ollama API client for AI-powered code explanations
"""
import json
import logging
import time
import ast
from typing import Optional, List, Dict

import requests

import config

logger = logging.getLogger(__name__)


class OllamaClient:
    def __init__(self, base_url: str = None, model: str = None):
        self.base_url = base_url or config.OLLAMA_BASE_URL
        self.model = model or config.OLLAMA_DEFAULT_MODEL
        self.session = requests.Session()
        self.session.headers["Content-Type"] = "application/json"

    def is_available(self) -> bool:
        """Check if Ollama is running"""
        try:
            response = self.session.get(f"{self.base_url}/api/tags", timeout=5)
            return response.status_code == 200
        except Exception:
            return False

    def get_available_models(self) -> List[str]:
        """Get list of available models"""
        try:
            response = self.session.get(f"{self.base_url}/api/tags", timeout=5)
            if response.status_code == 200:
                data = response.json()
                return [m["name"] for m in data.get("models", [])]
        except Exception as e:
            logger.debug(f"Could not get models: {e}")
        return []

    def explain_code(self, code: str, language: str = None) -> str:
        """Standard code explanation"""
        prompt = f"""You are a code explanation assistant. Explain the following code in detail.
Focus on:
- What the code does
- How it works
- Key components and their purpose

{"Language: " + language if language else ""}

Code:
```{language or ''}
{code}
```"""
        return self._generate(prompt)

    def run_analysis_agent(self, code: str, language: str = None) -> str:
        """Run an autonomous analysis agent (optimized for Kimi-k2.5:cloud)"""
        prompt = f"""You are an elite Software Architecture Agent (using {self.model}). 
Perform a deep, structured analysis of the provided code.

### ANALYSIS STEPS:
1. **Structural Intent**: What is the architectural goal of this code?
2. **Logic Breakdown**: Step-by-step trace of how the data/logic flows.
3. **Optimizations & Security**: Identify potential bottlenecks, bugs, or security risks.
4. **Architect's Verdict**: Final rating/conclusion on the code quality.

{"Language Context: " + language if language else ""}

CODE TO ANALYZE:
```{language or ''}
{code}
```

Provide the analysis in a professional, structured markdown format."""
        
        return self._generate(prompt)

    def summarize_project(self, readme: str, repo_name: str = None) -> str:
        """Summarize a project based on its README"""
        prompt = f"""You are a project summarization assistant. Based on the following README,
provide a concise summary of the project including:
- What the project does
- Key features
- Technology stack
- How to get started

{f"Project: {repo_name}" if repo_name else ""}

README:
{readme}

Provide a clear summary:"""

        return self._generate(prompt)

    def perform_architectural_audit(self, context: dict) -> str:
        """Analyze project-wide context to provide an architectural audit"""
        # If Ollama is available, attempt LLM audit
        if self.is_available():
            file_tree = "\n".join(context.get("file_tree", []))
            key_files_content = ""
            for path, content in context.get("key_files", {}).items():
                key_files_content += f"\nFILE: {path}\n---\n{content}\n---\n"

            prompt = f"""You are a Lead Software Architect. Perform a deep Architectural Audit of this project.

### PROJECT CONTEXT:
**File Tree (Partial):**
```
{file_tree}
```

**Key Configuration/Source Files:**
{key_files_content}

### YOUR AUDIT TASKS:
1. **Architectural Pattern**: Identify the main pattern (e.g., MVC, Layered, Event-Driven).
2. **Tech Stack Insights**: Analyze the dependencies and entry points.
3. **Scalability & Health**: Identify potential bottlenecks or architectural "smells".
4. **Strategic Roadmap**: Suggestions for the next 3 major improvements.

Provide a comprehensive, high-level report in structured markdown."""
            
            result = self._generate(prompt, temperature=0.3)
            if not result.startswith("Error:"):
                return result
            logger.warning(f"Ollama audit failed ({result}), falling back to Heuristic Engine.")

        # Fallback to Built-in Heuristic Architecture Engine
        return self.perform_heuristic_audit(context)

    def perform_heuristic_audit(self, context: dict) -> str:
        """
        Built-in Heuristic Architectural Analyzer.
        Runs when Ollama is offline or unavailable.
        Analyzes directory topologies, anchor files, and dependencies to synthesize
        an accurate architectural report.
        """
        file_tree = context.get("file_tree", [])
        key_files = context.get("key_files", {})
        
        # 1. Detect Languages and Frameworks
        tree_str = " ".join(file_tree).lower()
        key_content_str = " ".join(str(v) for v in key_files.values()).lower()
        
        patterns = []
        stack = []
        bottlenecks = []
        roadmap = []
        
        # Pattern Detection
        if any("docker-compose" in f for f in file_tree) or any("dockerfile" in f for f in file_tree):
            patterns.append("Containerized Microservice / Deployment-Ready")
            stack.append("Docker / Containerization")
        
        if any(x in tree_str for x in ["controllers", "views", "models"]) or any(x in tree_str for x in ["routes", "handlers"]):
            patterns.append("Layered / MVC (Model-View-Controller) Web Architecture")
        elif any(x in tree_str for x in ["src/components", "src/pages", "src/app", "components"]):
            patterns.append("Component-Driven SPA / Client Architecture")
        elif any(x in tree_str for x in ["cli", "cmd", "commands"]) or "click" in key_content_str or "argparse" in key_content_str:
            patterns.append("Modular CLI (Command Line Interface) Architecture")
        else:
            patterns.append("Modular Monolithic Library Architecture")

        # Stack Detection
        if "fastapi" in key_content_str or "uvicorn" in key_content_str:
            stack.append("FastAPI (High-performance Async Python)")
        if "flask" in key_content_str:
            stack.append("Flask (Python Microframework)")
        if "react" in key_content_str:
            stack.append("React.js Framework")
        if "vue" in key_content_str:
            stack.append("Vue.js Framework")
        if "sqlalchemy" in key_content_str:
            stack.append("SQLAlchemy ORM")
        if "pydantic" in key_content_str:
            stack.append("Pydantic Data Validation")
        if "pytest" in key_content_str or any("test" in f for f in file_tree):
            stack.append("Pytest / Automated Test Suite")
        if any(".github/workflows" in f for f in file_tree):
            stack.append("GitHub Actions CI/CD Pipeline")
        
        if not stack:
            if any(f.endswith(".py") for f in file_tree):
                stack.append("Standard Python 3 Runtime")
            elif any(f.endswith((".js", ".ts", ".jsx", ".tsx")) for f in file_tree):
                stack.append("Node.js / TypeScript Ecosystem")
            elif any(f.endswith(".go") for f in file_tree):
                stack.append("Go (Golang) Systems Stack")
            elif any(f.endswith(".rs") for f in file_tree):
                stack.append("Rust Cargo Ecosystem")
            else:
                stack.append("Polyglot Open-Source Stack")

        # Health & Bottlenecks
        has_tests = any("test" in f.lower() for f in file_tree)
        has_ci = any(".github" in f for f in file_tree)
        has_docs = any(x in tree_str for x in ["doc", "docs", "readme.md"])
        
        if not has_tests:
            bottlenecks.append("Absence of dedicated unit/integration test directory.")
            roadmap.append("Establish test harness (e.g. `pytest` or `vitest`) with >75% coverage.")
        else:
            roadmap.append("Expand existing integration test matrix across multiple runtimes.")

        if not has_ci:
            bottlenecks.append("Missing automated CI/CD workflow configuration.")
            roadmap.append("Configure GitHub Actions workflow for linting, type-checks, and automated testing.")
        
        if not any("docker" in f.lower() for f in file_tree):
            roadmap.append("Add containerization (`Dockerfile`, `docker-compose.yml`) for reproducible developer onboarding.")

        bottlenecks.append("Monitor third-party dependency vulnerabilities and license parity.")
        roadmap.append("Generate automated OpenAPI/Sphinx documentation for public interfaces.")

        # AST-level inspection for Python files
        ast_classes = []
        ast_imports = []
        ast_async_fns = 0
        ast_fns = 0
        
        for fname, content in key_files.items():
            if fname.endswith(".py") and content and not content.startswith("[File too large"):
                try:
                    parsed_ast = ast.parse(content)
                    for node in ast.walk(parsed_ast):
                        if isinstance(node, ast.ClassDef):
                            ast_classes.append(node.name)
                        elif isinstance(node, ast.FunctionDef):
                            ast_fns += 1
                        elif isinstance(node, ast.AsyncFunctionDef):
                            ast_async_fns += 1
                        elif isinstance(node, ast.Import):
                            for n in node.names:
                                ast_imports.append(n.name.split('.')[0])
                        elif isinstance(node, ast.ImportFrom):
                            if node.module:
                                ast_imports.append(node.module.split('.')[0])
                except Exception:
                    pass

        # Formatting Output
        report = f"""# 🏛️ Project Oracle Architectural Audit
> *Generated by Built-in Heuristic & AST Analysis Engine*
> *Mode: Heuristic / Structural Pattern Synthesis (Ollama not connected or offline)*

---

### 1. 📐 Architectural Pattern & Topology
- **Primary Identified Pattern:** {patterns[0]}
{f"- **Secondary Attributes:** {', '.join(patterns[1:])}" if len(patterns) > 1 else ""}
- **Total Tracked Files Analyzed:** {len(file_tree)} files
- **Modularity Score:** {"High (Separation of concerns detected)" if len(file_tree) > 15 else "Standard (Compact project layout)"}
{f"- **AST Classes Detected:** {', '.join(ast_classes[:6])}" if ast_classes else ""}
{f"- **Coroutine Concurrency:** {ast_async_fns} async functions (High-throughput async execution)" if ast_async_fns > 0 else ""}
{f"- **AST Dependency Footprint:** {', '.join(sorted(set(ast_imports))[:8])}" if ast_imports else ""}

---

### 2. 🧰 Technology Stack & Entry Points
- **Core Ecosystem:** {', '.join(stack)}
- **CI / Automation Status:** {"✅ Automated Workflows Present" if has_ci else "⚠️ No CI Workflows Detected"}
- **Testing Infrastructure:** {"✅ Tests Present" if has_tests else "⚠️ Minimal or Non-Standard Test Setup"}
- **Documentation Status:** {"✅ Documentation Found" if has_docs else "⚠️ Limited Documentation"}

---

### 3. 🔍 Scalability, Debt & Bottleneck Evaluation
"""
        for b in bottlenecks:
            report += f"- ⚠️ **Attention:** {b}\n"
        
        report += "\n---\n\n### 4. 🗺️ Strategic Architectural Roadmap\n"
        for i, r in enumerate(roadmap[:3], 1):
            report += f"{i}. **Action Item {i}:** {r}\n"
        
        report += "\n---\n*Tip: Connect a local Ollama instance (with `llama3.2` or `kimi-k2.5:cloud`) for deep neural reasoning and AST inspection.*"
        return report

    def suggest_smart_tags(self, readme: str, context: dict) -> List[str]:
        """Generate 3-5 high-relevance tags based on project context"""
        if self.is_available():
            file_tree = "\n".join(context.get("file_tree", []))
            
            prompt = f"""Analyze this project and generate 3-5 high-relevance 'Smart Tags' (short descriptive phrases).
Tags should describe the project's purpose, architecture, or unique features.

### CONTEXT:
**README Snippet:**
{readme[:2000] if readme else "No README available"}

**File Structure Overview:**
```
{file_tree}
```

**Output Format:** Just the tags separated by commas. No explanation.
Example Output: Event-Driven, Microservice-Ready, React-Frontend, Scalable-API"""

            response = self._generate(prompt, temperature=0.5)
            if isinstance(response, str) and not response.startswith("Error:"):
                tags = [t.strip() for t in response.split(",") if t.strip()]
                if tags:
                    return tags[:5]

        # Heuristic smart tags fallback
        file_tree_str = " ".join(context.get("file_tree", [])).lower()
        key_content_str = " ".join(str(v) for v in context.get("key_files", {}).values()).lower()
        tags = []

        if "fastapi" in key_content_str: tags.append("FastAPI")
        elif "flask" in key_content_str: tags.append("Flask")
        elif "django" in key_content_str: tags.append("Django")
        elif "react" in key_content_str: tags.append("React")
        elif "vue" in key_content_str: tags.append("Vue")
        
        if "docker" in file_tree_str or "docker" in key_content_str: tags.append("Dockerized")
        if "sqlite" in key_content_str or "sqlalchemy" in key_content_str: tags.append("Database-Backed")
        if "async" in key_content_str or "asyncio" in key_content_str: tags.append("Async-I/O")
        if ".github/workflows" in file_tree_str: tags.append("CI/CD-Ready")
        if "test" in file_tree_str: tags.append("Unit-Tested")
        if "ai" in readme.lower() or "llm" in readme.lower() or "ollama" in readme.lower(): tags.append("AI-Powered")
        
        if not tags:
            tags = ["Open-Source", "Modular", "Modern-Architecture"]
            
        return tags[:5]
        return tags[:5]

    def get_news(self, repo_name: str, readme: str = None, releases: List[Dict] = None) -> str:
        """Get latest news/updates about a project"""
        context = f"Project: {repo_name}\n"
        if readme:
            context += f"Description: {readme[:500]}...\n"
        if releases:
            context += "Recent releases:\n"
            for r in releases[:5]:
                context += f"- {r.get('name', 'Unknown')}: {r.get('tag_name', '')}\n"

        prompt = f"""Based on the following information about an open source project,
provide the latest news and updates:

{context}

Provide a summary of recent activity and any notable updates:"""

        return self._generate(prompt)

    def chat(self, message: str, context: str = None) -> str:
        """Chat with Ollama about a project"""
        prompt = message
        if context:
            prompt = f"""Context about the project:
{context}

User question: {message}

Please answer based on the context provided:"""

        return self._generate(prompt)

    def _generate(self, prompt: str, temperature: float = 0.7, max_tokens: int = 2000, retries: int = 3) -> str:
        """Generate a response using Ollama with retry logic"""
        last_error = None
        
        for attempt in range(retries):
            try:
                payload = {
                    "model": self.model,
                    "prompt": prompt,
                    "temperature": temperature,
                    "stream": False
                }
                # Adjust for cloud-based providers if needed (Ollama proxy)
                if "cloud" in self.model:
                    payload["options"] = {"num_predict": max_tokens}
                else:
                    payload["max_tokens"] = max_tokens

                response = self.session.post(
                    f"{self.base_url}/api/generate",
                    json=payload,
                    timeout=120
                )

                if response.status_code == 200:
                    data = response.json()
                    return data.get("response", "").strip()
                
                last_error = f"Ollama error: {response.status_code} - {response.text}"
                logger.error(last_error)
                
                if response.status_code in [500, 502, 503, 504] and attempt < retries - 1:
                    wait = 2 ** attempt
                    time.sleep(wait)
                    continue
                else:
                    break

            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
                last_error = str(e)
                if attempt < retries - 1:
                    wait = 2 ** attempt
                    logger.warning(f"Ollama connection error (attempt {attempt+1}/{retries}). Retrying in {wait}s: {e}")
                    time.sleep(wait)
                else:
                    break
            except Exception as e:
                last_error = str(e)
                logger.error(f"Unexpected error in Ollama call: {e}")
                break
        
        return f"Error: {last_error or 'Unknown failure'}"

    def set_model(self, model: str):
        """Change the current model"""
        self.model = model


# Singleton
_ollama_client = None


def get_ollama_client() -> OllamaClient:
    """Get Ollama client singleton"""
    global _ollama_client
    if _ollama_client is None:
        _ollama_client = OllamaClient()
    return _ollama_client
