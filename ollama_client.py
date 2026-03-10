"""
Ollama API client for AI-powered code explanations
"""
import json
import logging
import time
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
        
        return self._generate(prompt, temperature=0.3)

    def suggest_smart_tags(self, readme: str, context: dict) -> List[str]:
        """Generate 3-5 high-relevance tags based on project context"""
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
        # Handle potential list or comma-separated string
        if isinstance(response, str):
            tags = [t.strip() for t in response.split(",") if t.strip()]
        else:
            tags = []
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
