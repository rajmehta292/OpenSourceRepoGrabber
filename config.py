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
OLLAMA_DEFAULT_MODEL = "kimi-k2.5:cloud"
OLLAMA_MODELS = ["kimi-k2.5:cloud", "llama3.2", "qwen2.5", "mistral", "phi3"]

# UI Settings
WINDOW_MIN_WIDTH = 1200
WINDOW_MIN_HEIGHT = 800
WINDOW_DEFAULT_WIDTH = 1400
WINDOW_DEFAULT_HEIGHT = 900
THEME_PATH = BASE_DIR / "apple_theme.json"
DEFAULT_APPEARANCE_MODE = "system" # "light", "dark", or "system"

# Earthy Glassmorphism palette
COLORS = {
    "light": {
        "bg": "#E8EBE4",      # Sage Green tint
        "card": "#F2F0E6",    # Sand
        "text": "#1D1D1F",
        "accent": "#5E6C54",  # Muted Forest
        "success": "#768969",
        "error": "#B85C5C",
        "border": "#D1D5CB"
    },
    "dark": {
        "bg": "#0B120E",      # Deeper Midnight Emerald
        "card": "#151D18",    # Dark Emerald Glass
        "text": "#ECF0ED",    # High-contrast Mint White
        "accent": "#10B981",  # Vibrant Emerald
        "success": "#34D399",
        "error": "#EF4444",
        "border": "#202924"
    }
}
