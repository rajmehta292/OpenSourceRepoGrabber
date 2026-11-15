"""
OpenSource Repo Grabber (OSRG) - Hardware-Accelerated WebView2 Host & API Bridge
Hosts the React + Meta Astryx frontend inside pywebview (Edge Chromium WebView2).
"""
from __future__ import annotations

import logging
import os
import sys
import webbrowser
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import webview

import config
from contributor_guide import (
    CONVENTIONAL_COMMITS,
    FIRST_PR_WORKFLOW,
    GIT_ESSENTIALS,
)
from database import get_database
from github_api import (
    CURATED_STARTER_REPOS,
    LICENSE_KNOWLEDGE_BASE,
    get_github_client,
)
from models import RepoCategory, Repository
from ollama_client import get_ollama_client
from repo_manager import get_repo_manager

logger = logging.getLogger(__name__)

FRONTEND_DIST_DIR = Path(__file__).resolve().parent / "frontend" / "dist"
ASSETS_ICON_PATH = Path(__file__).resolve().parent / "assets" / "icon.ico"
MAX_LOCAL_FILE_BYTES = 160_000


def _json_safe(value: Any) -> Any:
    """Recursively convert datetime, Path, and Enum values into JSON-serializable primitives."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(v) for v in value]
    if hasattr(value, "value"):
        return _json_safe(value.value)
    return str(value)


def _serialize_rate_limit(rate: Dict[str, Any]) -> Dict[str, Any]:
    reset_val = rate.get("reset")
    reset_display = ""
    if isinstance(reset_val, datetime):
        reset_display = reset_val.strftime("%H:%M")
    return {
        "limit": int(rate.get("limit", 0) or 0),
        "remaining": int(rate.get("remaining", 0) or 0),
        "used": int(rate.get("used", 0) or 0),
        "reset": _json_safe(reset_val),
        "reset_display": reset_display,
        "authenticated": bool(rate.get("authenticated", False)),
        "rate_limited": bool(rate.get("rate_limited", False)),
    }


def _serialize_local_repo(repo: Dict[str, Any]) -> Dict[str, Any]:
    out = _json_safe(dict(repo))
    out.setdefault("smart_tags", [])
    return out


class OSRGApi:
    """JSON-serializable bridge exposed to the React + Meta Astryx frontend."""

    def __init__(self) -> None:
        self._window: Optional[webview.Window] = None
        self._trending_cache: Dict[str, List[Dict[str, Any]]] = {}
        self._search_cache: Dict[str, List[Dict[str, Any]]] = {}
        self._gfi_cache: Dict[str, List[Dict[str, Any]]] = {}

    def attach_window(self, window: webview.Window) -> None:
        self._window = window

    def ping(self) -> Dict[str, Any]:
        return {"ok": True, "version": "2.0.0"}

    # ------------------------------------------------------------------
    # Overview & System Status
    # ------------------------------------------------------------------
    def get_overview_data(self) -> Dict[str, Any]:
        try:
            rm = get_repo_manager()
            gh = get_github_client()
            ollama = get_ollama_client()

            local_repos = rm.list_repos()
            folders = rm.get_all_license_folders()
            rate = _serialize_rate_limit(gh.get_rate_limit_status())
            ollama_ok = ollama.is_available()

            return {
                "ok": True,
                "repos_path": str(rm.get_repos_path()),
                "local_count": len(local_repos),
                "folders": folders,
                "rate_limit": rate,
                "ollama": {
                    "available": ollama_ok,
                    "model": ollama.model,
                    "base_url": ollama.base_url,
                },
                "starter_repos": CURATED_STARTER_REPOS,
            }
        except Exception as exc:
            logger.exception("get_overview_data failed")
            return {"ok": False, "error": str(exc)}

    def get_rate_limit(self, force_refresh: bool = False) -> Dict[str, Any]:
        try:
            gh = get_github_client()
            rate = _serialize_rate_limit(gh.get_rate_limit_status(force_refresh=bool(force_refresh)))
            return {"ok": True, "rate_limit": rate}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def set_github_token(self, token: str) -> Dict[str, Any]:
        try:
            cleaned = (token or "").strip()
            gh = get_github_client()
            gh.set_token(cleaned)
            rate = _serialize_rate_limit(gh.get_rate_limit_status(force_refresh=True))
            return {"ok": True, "rate_limit": rate}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    # ------------------------------------------------------------------
    # Discovery: Trending, Search, Remote README
    # ------------------------------------------------------------------
    def search_trending_repos(self, language: str = "", force_refresh: bool = False) -> Dict[str, Any]:
        try:
            lang = (language or "").strip()
            cache_key = lang.lower() or "all"
            gh = get_github_client()

            if not force_refresh and cache_key in self._trending_cache:
                items = self._trending_cache[cache_key]
            else:
                items = _json_safe(gh.search_trending_repos(language=lang))
                self._trending_cache[cache_key] = items

            rate = _serialize_rate_limit(gh.get_rate_limit_status())
            return {"ok": True, "items": items, "rate_limit": rate, "cached": not force_refresh}
        except Exception as exc:
            logger.exception("search_trending_repos failed")
            return {"ok": False, "error": str(exc), "items": []}

    def search_repos(self, query: str = "", language: str = "All", force_refresh: bool = False) -> Dict[str, Any]:
        try:
            q = (query or "").strip()
            if not q:
                return {"ok": True, "items": [], "rate_limit": _serialize_rate_limit(get_github_client().get_rate_limit_status())}

            lang = (language or "All").strip()
            lang_arg = None if lang.lower() in ("", "all") else lang
            cache_key = f"{q.lower()}::{lang.lower()}"
            gh = get_github_client()

            if not force_refresh and cache_key in self._search_cache:
                items = self._search_cache[cache_key]
            else:
                items = _json_safe(gh.search_repos(q, language=lang_arg))
                self._search_cache[cache_key] = items

            rate = _serialize_rate_limit(gh.get_rate_limit_status())
            return {"ok": True, "items": items, "rate_limit": rate}
        except Exception as exc:
            logger.exception("search_repos failed")
            return {"ok": False, "error": str(exc), "items": []}

    def get_remote_readme(self, full_name: str) -> Dict[str, Any]:
        try:
            gh = get_github_client()
            content = gh.get_remote_readme((full_name or "").strip())
            if not content:
                return {"ok": True, "content": "", "found": False}
            return {"ok": True, "content": content, "found": True}
        except Exception as exc:
            return {"ok": False, "error": str(exc), "content": "", "found": False}

    # ------------------------------------------------------------------
    # OSS Launchpad: Good First Issues, License Decoder, PR Guide
    # ------------------------------------------------------------------
    def search_good_first_issues(self, language: str = "All", topic: str = "", force_refresh: bool = False) -> Dict[str, Any]:
        try:
            lang = (language or "All").strip()
            lang_arg = None if lang.lower() in ("", "all") else lang
            topic_arg = (topic or "").strip() or None
            cache_key = f"{lang.lower()}::{(topic_arg or '').lower()}"
            gh = get_github_client()

            if not force_refresh and cache_key in self._gfi_cache:
                items = self._gfi_cache[cache_key]
            else:
                items = _json_safe(gh.search_good_first_issues(language=lang_arg, topic=topic_arg))
                self._gfi_cache[cache_key] = items

            return {"ok": True, "items": items}
        except Exception as exc:
            logger.exception("search_good_first_issues failed")
            return {"ok": False, "error": str(exc), "items": []}

    def get_license_knowledge_base(self) -> Dict[str, Any]:
        return {"ok": True, "licenses": LICENSE_KNOWLEDGE_BASE}

    def get_contributor_guide(self) -> Dict[str, Any]:
        return {
            "ok": True,
            "workflow": FIRST_PR_WORKFLOW,
            "git_essentials": GIT_ESSENTIALS,
            "conventional_commits": [
                {"type": t, "description": d} for t, d in CONVENTIONAL_COMMITS
            ],
        }

    # ------------------------------------------------------------------
    # Local Repositories: List, Clone, Sync, Delete, Tree, File Inspector
    # ------------------------------------------------------------------
    def list_local_repos(self, license_filter: str = "ALL") -> Dict[str, Any]:
        try:
            rm = get_repo_manager()
            filt = None if not license_filter or license_filter.upper() == "ALL" else license_filter
            repos = [_serialize_local_repo(r) for r in rm.list_repos(license_filter=filt)]
            all_repos = repos if filt is None else rm.list_repos()
            counts: Dict[str, int] = {"ALL": len(all_repos)}
            for r in all_repos:
                lic = r.get("license") or "Other"
                counts[lic] = counts.get(lic, 0) + 1
            return {
                "ok": True,
                "repos": repos,
                "counts": counts,
                "repos_path": str(rm.get_repos_path()),
            }
        except Exception as exc:
            logger.exception("list_local_repos failed")
            return {"ok": False, "error": str(exc), "repos": []}

    def clone_repo(self, repo_url: str, license_spdx: Optional[str] = None) -> Dict[str, Any]:
        try:
            target = (repo_url or "").strip()
            if not target:
                return {"ok": False, "error": "Please enter a repository URL or owner/repo."}

            rm = get_repo_manager()
            result = rm.add_repo(target, license_spdx=license_spdx)
            if not result or "error" in result:
                err = (result or {}).get("error", "Clone failed.")
                return {"ok": False, "error": err}

            repo_path = result.get("path", "")
            full_name = result.get("full_name") or result.get("name", "")
            tags: List[str] = []

            try:
                readme = rm.get_repo_readme(repo_path) or ""
                ctx = rm.get_project_context(repo_path)
                tags = get_ollama_client().suggest_smart_tags(readme, ctx) or []

                db = get_database()
                existing = db.get_repository(full_name=full_name)
                if existing:
                    existing.smart_tags = tags
                    db.save_repository(existing)
                else:
                    db_repo = Repository(
                        id=abs(hash(full_name)) % 10**9,
                        name=result.get("name", full_name.split("/")[-1]),
                        full_name=full_name,
                        description=f"Local cloned repository at {repo_path}",
                        html_url=f"https://github.com/{full_name}",
                        clone_url=f"https://github.com/{full_name}.git",
                        stars=0,
                        forks=0,
                        watchers=0,
                        open_issues=0,
                        license=result.get("license", "Other"),
                        license_spdx_id=license_spdx or result.get("license", "Other"),
                        language=None,
                        topics=[],
                        created_at=datetime.now(),
                        updated_at=datetime.now(),
                        pushed_at=datetime.now(),
                        category=RepoCategory.CLONED,
                        smart_tags=tags,
                    )
                    db.save_repository(db_repo)
            except Exception as meta_err:
                logger.warning(f"Metadata/tag generation skipped during clone: {meta_err}")

            return {
                "ok": True,
                "result": {
                    "name": result.get("name", ""),
                    "full_name": full_name,
                    "path": str(repo_path),
                    "license": result.get("license", "Other"),
                    "status": result.get("status", "cloned"),
                    "smart_tags": tags,
                },
            }
        except Exception as exc:
            logger.exception("clone_repo failed")
            return {"ok": False, "error": str(exc)}

    def update_local_repo(self, repo_path: str) -> Dict[str, Any]:
        try:
            res = get_repo_manager().update_repo(repo_path)
            return {"ok": "error" not in res, **res}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def update_all_repos(self) -> Dict[str, Any]:
        try:
            results = get_repo_manager().update_all_repos()
            updated = sum(1 for r in results if r.get("status") == "updated")
            errors = [r for r in results if "error" in r]
            return {
                "ok": True,
                "total": len(results),
                "updated": updated,
                "errors": errors,
                "results": results,
            }
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def delete_local_repo(self, repo_path: str) -> Dict[str, Any]:
        try:
            res = get_repo_manager().delete_repo(repo_path)
            return {"ok": "error" not in res, **res}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def get_local_readme(self, repo_path: str) -> Dict[str, Any]:
        try:
            content = get_repo_manager().get_repo_readme(repo_path) or ""
            return {"ok": True, "content": content, "found": bool(content)}
        except Exception as exc:
            return {"ok": False, "error": str(exc), "content": "", "found": False}

    def get_local_file_tree(self, repo_path: str, max_files: int = 250) -> Dict[str, Any]:
        try:
            rm = get_repo_manager()
            stats = rm.get_repo_stats(repo_path)
            files = rm.get_repo_file_tree(repo_path, max_files=int(max_files))
            return {"ok": True, "stats": stats, "files": files}
        except Exception as exc:
            return {"ok": False, "error": str(exc), "stats": {}, "files": []}

    def read_local_file(self, repo_path: str, rel_path: str) -> Dict[str, Any]:
        """Safely read a single text file inside a cloned repository for instant preview."""
        try:
            root = Path(repo_path).resolve()
            target = (root / rel_path).resolve()
            if root not in target.parents and target != root:
                return {"ok": False, "error": "Access denied: path outside repository."}
            if not target.is_file():
                return {"ok": False, "error": "Not a file."}

            size = target.stat().st_size
            raw = target.read_bytes()[:MAX_LOCAL_FILE_BYTES]
            if b"\x00" in raw:
                return {"ok": False, "error": f"Binary file ({size:,} bytes) cannot be previewed as text."}

            text = raw.decode("utf-8", errors="replace")
            truncated = size > MAX_LOCAL_FILE_BYTES
            return {
                "ok": True,
                "path": rel_path.replace("\\", "/"),
                "size": size,
                "truncated": truncated,
                "content": text,
            }
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def run_architectural_audit(
        self, repo_path: str, full_name: str = "", force: bool = False
    ) -> Dict[str, Any]:
        try:
            db = get_database()
            target_name = (full_name or Path(repo_path).name).strip()
            existing = db.get_repository(full_name=target_name)
            if not force and existing and existing.architectural_audit:
                return {
                    "ok": True,
                    "report": existing.architectural_audit,
                    "smart_tags": existing.smart_tags or [],
                    "cached": True,
                }

            rm = get_repo_manager()
            ollama = get_ollama_client()
            context = rm.get_project_context(repo_path)
            report = ollama.perform_architectural_audit(context)

            tags = existing.smart_tags if existing else []
            if not tags:
                readme = rm.get_repo_readme(repo_path) or ""
                tags = ollama.suggest_smart_tags(readme, context) or []

            if existing:
                existing.architectural_audit = report
                existing.smart_tags = tags
                db.save_repository(existing)
            else:
                db_repo = Repository(
                    id=abs(hash(target_name)) % 10**9,
                    name=Path(repo_path).name,
                    full_name=target_name,
                    description=f"Local audited repository at {repo_path}",
                    html_url=f"https://github.com/{target_name}",
                    clone_url=f"https://github.com/{target_name}.git",
                    stars=0,
                    forks=0,
                    watchers=0,
                    open_issues=0,
                    license=Path(repo_path).parent.name,
                    license_spdx_id=Path(repo_path).parent.name,
                    language=None,
                    topics=[],
                    created_at=datetime.now(),
                    updated_at=datetime.now(),
                    pushed_at=datetime.now(),
                    category=RepoCategory.CLONED,
                    architectural_audit=report,
                    smart_tags=tags,
                )
                db.save_repository(db_repo)

            return {
                "ok": True,
                "report": report,
                "smart_tags": tags,
                "cached": False,
                "ollama_available": ollama.is_available(),
            }
        except Exception as exc:
            logger.exception("run_architectural_audit failed")
            return {"ok": False, "error": str(exc)}

    def open_in_editor(self, repo_path: str, preferred: str = "auto") -> Dict[str, Any]:
        try:
            opened = get_repo_manager().open_in_editor(repo_path, preferred=preferred)
            return {"ok": bool(opened)}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def open_in_explorer(self, repo_path: str = "") -> Dict[str, Any]:
        try:
            rm = get_repo_manager()
            if repo_path:
                rm.open_in_explorer(repo_path)
            else:
                rm.open_folder()
            return {"ok": True}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def open_external_url(self, url: str) -> Dict[str, Any]:
        try:
            target = (url or "").strip()
            if not (target.startswith("https://") or target.startswith("http://")):
                return {"ok": False, "error": "Unsupported URL scheme."}
            webbrowser.open(target)
            return {"ok": True}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    # ------------------------------------------------------------------
    # AI Explain & Settings
    # ------------------------------------------------------------------
    def get_ai_status(self) -> Dict[str, Any]:
        try:
            ollama = get_ollama_client()
            available = ollama.is_available()
            models = ollama.get_available_models() if available else []
            return {
                "ok": True,
                "available": available,
                "models": models,
                "current_model": ollama.model,
                "base_url": ollama.base_url,
            }
        except Exception as exc:
            return {"ok": False, "error": str(exc), "available": False, "models": []}

    def refresh_ai_models(self, base_url: str = "") -> Dict[str, Any]:
        ollama = get_ollama_client()
        if base_url and base_url.strip():
            ollama.base_url = base_url.strip().rstrip("/")
        return self.get_ai_status()

    def set_ai_model(self, model: str) -> Dict[str, Any]:
        try:
            ollama = get_ollama_client()
            ollama.set_model((model or "").strip())
            return {"ok": True, "current_model": ollama.model}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def analyze_code(self, code: str, language: Optional[str] = None) -> Dict[str, Any]:
        try:
            snippet = (code or "").strip()
            if not snippet:
                return {"ok": False, "error": "Please enter code or a question to analyze."}
            ollama = get_ollama_client()
            result = ollama.run_analysis_agent(snippet, language=language)
            return {"ok": True, "analysis": result, "ollama_available": ollama.is_available()}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def set_ollama_url(self, url: str) -> Dict[str, Any]:
        try:
            cleaned = (url or "").strip().rstrip("/")
            if not cleaned.startswith(("http://", "https://")):
                return {"ok": False, "error": "URL must start with http:// or https://"}
            ollama = get_ollama_client()
            ollama.base_url = cleaned
            return self.get_ai_status()
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def get_settings(self) -> Dict[str, Any]:
        try:
            gh = get_github_client()
            ollama = get_ollama_client()
            rm = get_repo_manager()
            return {
                "ok": True,
                "repos_path": str(rm.get_repos_path()),
                "has_token": bool(gh.token),
                "ollama_url": ollama.base_url,
                "ollama_model": ollama.model,
                "rate_limit": _serialize_rate_limit(gh.get_rate_limit_status()),
            }
        except Exception as exc:
            return {"ok": False, "error": str(exc)}


def main() -> None:
    """Launch the OSRG WebView2 desktop window."""
    if not FRONTEND_DIST_DIR.exists() or not (FRONTEND_DIST_DIR / "index.html").exists():
        raise FileNotFoundError(
            f"Frontend build not found at {FRONTEND_DIST_DIR}. "
            "Run 'npm.cmd run build' in the frontend directory first."
        )

    api = OSRGApi()
    index_url = str((FRONTEND_DIST_DIR / "index.html").resolve())

    window = webview.create_window(
        title="OpenSource Repo Grabber — Discovery & Architecture Studio",
        url=index_url,
        js_api=api,
        width=config.WINDOW_WIDTH,
        height=config.WINDOW_HEIGHT,
        min_size=(config.MIN_WIDTH, config.MIN_HEIGHT),
        background_color="#0E1410",
    )
    api.attach_window(window)

    icon_arg = str(ASSETS_ICON_PATH) if ASSETS_ICON_PATH.exists() else None
    webview.start(gui="edgechromium", icon=icon_arg, http_server=True)


if __name__ == "__main__":
    main()
