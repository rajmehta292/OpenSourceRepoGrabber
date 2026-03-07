"""
Ollama API client for AI-powered code explanations
"""
import json
import logging
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
        """Explain code using Ollama"""
        prompt = f"""You are a code explanation assistant. Explain the following code in detail.
Focus on:
- What the code does
- How it works
- Key components and their purpose
- Any interesting patterns or techniques used

{"Language: " + language if language else ""}

Code to explain:
```{language or ''}
{code}
```

Provide a clear, detailed explanation:"""

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

    def _generate(self, prompt: str, temperature: float = 0.7, max_tokens: int = 2000) -> str:
        """Generate a response using Ollama"""
        try:
            payload = {
                "model": self.model,
                "prompt": prompt,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "stream": False
            }

            response = self.session.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=120
            )

            if response.status_code == 200:
                data = response.json()
                return data.get("response", "").strip()
            else:
                logger.error(f"Ollama error: {response.status_code} - {response.text}")
                return f"Error: Failed to get response from Ollama (status: {response.status_code})"

        except requests.exceptions.ConnectionError:
            return "Error: Cannot connect to Ollama. Please ensure Ollama is running on your system."
        except requests.exceptions.Timeout:
            return "Error: Request timed out. The model might be slow to respond."
        except Exception as e:
            logger.error(f"Ollama error: {e}")
            return f"Error: {str(e)}"

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
