"""
Configuration settings for OpenSource Repo Grabber
"""
import os
from pathlib import Path

# App Info
APP_NAME = "OpenSource Repo Grabber"
APP_VERSION = "1.0.0"

# Paths
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)
DB_PATH = DATA_DIR / "repos.db"
CACHE_DIR = DATA_DIR / "cache"
CACHE_DIR.mkdir(exist_ok=True)
CLONED_REPOS_DIR = DATA_DIR / "cloned_repos"

# GitHub API
GITHUB_API_BASE = "https://api.github.com"
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")  # Optional: for higher rate limits

# Licenses to track
LICENSES = ["mit", "apache-2.0", "bsd-3-clause", "bsd-2-clause"]

# Repository counts
TOP_REPOS_COUNT = 30
TRENDING_REPOS_COUNT = 30

# Scan intervals (in minutes)
SCAN_INTERVALS = {
    "15": 15,
    "30": 30,
    "60": 60,
    "120": 120
}
DEFAULT_SCAN_INTERVAL = 30

# Ollama settings
OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_DEFAULT_MODEL = "llama3.2"
OLLAMA_MODELS = ["llama3.2", "qwen2.5", "mistral", "phi3"]

# UI Settings
WINDOW_MIN_WIDTH = 1200
WINDOW_MIN_HEIGHT = 800
WINDOW_DEFAULT_WIDTH = 1400
WINDOW_DEFAULT_HEIGHT = 900

# Colors (matching SPEC.md)
COLORS = {
    "primary_bg": "#1a1a2e",
    "secondary_bg": "#16213e",
    "card_bg": "#0f3460",
    "accent": "#e94560",
    "success": "#00d9a0",
    "warning": "#ffc107",
    "error": "#ff4757",
    "text_primary": "#ffffff",
    "text_secondary": "#a0a0a0",
    "border": "#2a2a4a"
}
