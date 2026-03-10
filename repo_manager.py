"""
Repository Manager for OpenSource Repo Grabber
Organizes repos by license type into separate folders
"""
import os
import subprocess
import logging
import shutil
from pathlib import Path
from typing import Optional, List
from datetime import datetime

import config

logger = logging.getLogger(__name__)

# License folder mapping
LICENSE_FOLDERS = {
    "mit": "MIT",
    "apache-2.0": "Apache-2.0",
    "bsd-2-clause": "BSD-2-Clause",
    "bsd-3-clause": "BSD-3-Clause",
    "bsd-3-clause-clear": "BSD-3-Clause-Clear",
    "gpl-2.0": "GPL-2.0",
    "gpl-3.0": "GPL-3.0",
    "lgpl-2.1": "LGPL-2.1",
    "lgpl-3.0": "LGPL-3.0",
    "agpl-3.0": "AGPL-3.0",
    "mpl-2.0": "MPL-2.0",
    "unlicense": "Unlicense",
    "cc0-1.0": "CC0-1.0",
    "cc-by-4.0": "CC-BY-4.0",
    "zlib": "Zlib",
    "isc": "ISC",
    "0bsd": "0BSD",
    "other": "Other"
}

LICENSE_ALIASES = {
    "mit": "MIT",
    "apache-2.0": "Apache-2.0",
    "apache 2.0": "Apache-2.0",
    "bsd": "BSD-3-Clause",
    "bsd-2-clause": "BSD-2-Clause",
    "bsd-3-clause": "BSD-3-Clause",
    "gpl": "GPL-3.0",
    "gpl-2.0": "GPL-2.0",
    "gpl-3.0": "GPL-3.0",
    "lgpl": "LGPL-2.1",
    "lgpl-2.1": "LGPL-2.1",
    "lgpl-3.0": "LGPL-3.0",
    "agpl": "AGPL-3.0",
    "agpl-3.0": "AGPL-3.0",
    "unlicense": "Unlicense",
    "mpl": "MPL-2.0",
    "mpl-2.0": "MPL-2.0",
    "cc0": "CC0-1.0",
    "cc0-1.0": "CC0-1.0",
    "cc-by": "CC-BY-4.0",
    "cc-by-4.0": "CC-BY-4.0",
    "zlib": "Zlib",
    "isc": "ISC",
    "0bsd": "0BSD"
}


class RepoManager:
    def __init__(self, base_path: str = None):
        self.base_path = Path(base_path) if base_path else config.DATA_DIR / "repos"
        self.base_path.mkdir(parents=True, exist_ok=True)
        
        # Create license folders
        self._create_license_folders()
    
    def _create_license_folders(self):
        """Create all license folder directories"""
        for license_key, folder_name in LICENSE_FOLDERS.items():
            folder_path = self.base_path / folder_name
            folder_path.mkdir(parents=True, exist_ok=True)
    
    def _get_license_folder(self, license_spdx: str = None) -> Path:
        """Determine which folder to use based on license"""
        if not license_spdx:
            return self.base_path / "Other"
        
        # Normalize license key
        key = license_spdx.lower().strip()
        
        # Check for direct match
        if key in LICENSE_FOLDERS:
            return self.base_path / LICENSE_FOLDERS[key]
        
        # Check aliases
        if key in LICENSE_ALIASES:
            folder_name = LICENSE_ALIASES[key]
            return self.base_path / folder_name
        
        return self.base_path / "Other"
    
    def get_repos_path(self) -> Path:
        """Return the repos folder path"""
        return self.base_path
    
    def get_all_license_folders(self) -> dict:
        """Get all license folders with their paths and repo counts"""
        folders = {}
        for license_key, folder_name in LICENSE_FOLDERS.items():
            folder_path = self.base_path / folder_name
            if folder_path.exists():
                repos = list(folder_path.iterdir())
                repos = [r for r in repos if r.is_dir()]
                folders[folder_name] = {
                    "path": str(folder_path),
                    "count": len(repos)
                }
        return folders
    
    def get_repo_license_from_github(self, full_name: str) -> str:
        """Fetch license from GitHub API"""
        try:
            import requests
            url = f"https://api.github.com/repos/{full_name}"
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                return data.get("license", {}).get("spdx_id", "")
        except Exception as e:
            logger.error(f"Error fetching license: {e}")
        return None
    
    def add_repo(self, repo_url: str, license_spdx: str = None) -> Optional[dict]:
        """
        Add a repository by URL or full_name (e.g., 'facebook/react')
        Returns dict with name, path, status
        """
        try:
            # Parse the repo info from URL or name
            if "github.com" in repo_url:
                parts = repo_url.rstrip("/").split("/")
                if "github.com" in parts:
                    idx = parts.index("github.com")
                    if len(parts) > idx + 2:
                        owner = parts[idx + 1]
                        name = parts[idx + 2].replace(".git", "")
                    else:
                        return {"error": "Invalid GitHub URL format"}
                else:
                    return {"error": "Not a valid GitHub URL"}
            else:
                parts = repo_url.strip().split("/")
                if len(parts) != 2:
                    return {"error": "Please use format: owner/repo or full GitHub URL"}
                owner, name = parts[0], parts[1]
            
            full_name = f"{owner}/{name}"
            
            # Get license if not provided
            if not license_spdx:
                license_spdx = self.get_repo_license_from_github(full_name)
            
            # Determine target folder
            target_folder = self._get_license_folder(license_spdx)
            repo_path = target_folder / f"{owner}_{name}"
            
            # Check if already exists in any folder
            for license_folder in LICENSE_FOLDERS.values():
                check_path = self.base_path / license_folder / f"{owner}_{name}"
                if check_path.exists():
                    return {
                        "name": full_name,
                        "path": str(check_path),
                        "license": license_folder,
                        "status": "already_exists",
                        "message": f"Repository already cloned at {check_path}"
                    }
            
            # Clone the repo
            clone_url = f"https://github.com/{full_name}.git"
            result = subprocess.run(
                ["git", "clone", "--depth", "1", clone_url, str(repo_path)],
                capture_output=True,
                timeout=300
            )
            
            if result.returncode == 0:
                return {
                    "name": full_name,
                    "path": str(repo_path),
                    "license": license_spdx or "Unknown",
                    "folder": target_folder.name,
                    "status": "cloned",
                    "message": f"Successfully cloned {full_name} to {target_folder.name}"
                }
            else:
                error = result.stderr.decode() if result.stderr else "Unknown error"
                return {
                    "name": full_name,
                    "error": error,
                    "status": "failed"
                }
                
        except subprocess.TimeoutExpired:
            return {"error": "Clone timed out", "status": "failed"}
        except Exception as e:
            return {"error": str(e), "status": "failed"}
    
    def update_repo(self, repo_path: str) -> dict:
        """Update a repository with git pull"""
        try:
            path = Path(repo_path)
            if not path.exists():
                return {"error": "Repository not found", "status": "failed"}
            
            # Try main branch first
            result = subprocess.run(
                ["git", "pull", "origin", "main"],
                cwd=path,
                capture_output=True,
                timeout=60
            )
            
            if result.returncode == 0:
                return {"status": "updated", "message": "Repository updated successfully"}
            else:
                # Try master branch
                result = subprocess.run(
                    ["git", "pull", "origin", "master"],
                    cwd=path,
                    capture_output=True,
                    timeout=60
                )
                if result.returncode == 0:
                    return {"status": "updated", "message": "Repository updated (master branch)"}
                return {"error": result.stderr.decode() if result.stderr else "Update failed", "status": "failed"}
        except Exception as e:
            return {"error": str(e), "status": "failed"}
    
    def update_all_repos(self) -> List[dict]:
        """Update all cloned repositories across all license folders"""
        results = []
        for license_folder in LICENSE_FOLDERS.values():
            folder_path = self.base_path / license_folder
            if folder_path.exists():
                for item in folder_path.iterdir():
                    if item.is_dir():
                        result = self.update_repo(str(item))
                        result["name"] = item.name
                        results.append(result)
        return results
    
    def delete_repo(self, repo_path: str) -> dict:
        """Delete a repository"""
        try:
            path = Path(repo_path)
            if not path.exists():
                return {"error": "Repository not found", "status": "failed"}
            
            shutil.rmtree(path)
            return {"status": "deleted", "message": "Repository deleted"}
        except Exception as e:
            return {"error": str(e), "status": "failed"}
    
    def move_repo_to_license_folder(self, repo_path: str, license_spdx: str) -> dict:
        """Move a repository to a different license folder"""
        try:
            path = Path(repo_path)
            if not path.exists():
                return {"error": "Repository not found", "status": "failed"}
            
            # Get current and target folders
            current_folder = path.parent.name
            target_folder = self._get_license_folder(license_spdx)
            
            if current_folder == target_folder.name:
                return {"status": "already_correct", "message": "Repository already in correct folder"}
            
            # Check if target folder already has a repo with same name
            repo_name = path.name
            target_path = target_folder / repo_name
            
            if target_path.exists():
                return {"error": f"A repo named {repo_name} already exists in {target_folder.name}", "status": "failed"}
            
            # Move the repo
            shutil.move(str(path), str(target_path))
            
            return {
                "status": "moved",
                "new_path": str(target_path),
                "new_folder": target_folder.name,
                "message": f"Moved to {target_folder.name}"
            }
        except Exception as e:
            return {"error": str(e), "status": "failed"}
    
    def list_repos(self, license_filter: str = None) -> List[dict]:
        """List all repositories, optionally filtered by license folder"""
        from database import get_database
        db = get_database()
        
        repos = []
        
        if license_filter:
            # Filter by specific license folder
            folders = [license_filter]
        else:
            # Get all license folders
            folders = list(LICENSE_FOLDERS.values())
        
        for folder_name in folders:
            folder_path = self.base_path / folder_name
            if not folder_path.exists():
                continue
                
            for item in folder_path.iterdir():
                if item.is_dir():
                    # Try to get git info
                    last_update = None
                    try:
                        result = subprocess.run(
                            ["git", "log", "-1", "--format=%ci"],
                            cwd=item,
                            capture_output=True,
                            timeout=10
                        )
                        if result.returncode == 0 and result.stdout:
                            last_update = result.stdout.decode().strip()
                    except:
                        pass
                    
                    # Cross-reference with DB for tags and audit
                    # Repo name on disk is 'owner_name'
                    repo_data = {
                        "name": item.name,
                        "path": str(item),
                        "license": folder_name,
                        "last_update": last_update,
                        "smart_tags": [],
                        "architectural_audit": None
                    }
                    
                    # Try to find in DB (full_name might be matches by restoring /)
                    db_repo = db.get_repository(full_name=item.name.replace("_", "/", 1))
                    if db_repo:
                        repo_data["smart_tags"] = db_repo.smart_tags
                        repo_data["architectural_audit"] = db_repo.architectural_audit
                    
                    repos.append(repo_data)
        
        return repos
    
    def get_repo_readme(self, repo_path: str) -> Optional[str]:
        """Get README from repository"""
        path = Path(repo_path)
        if not path.exists():
            return None
            
        readme_names = ["README.md", "README.rst", "README.txt", "README", "readme.md", "Readme.md"]
        for name in readme_names:
            readme_path = path / name
            if readme_path.exists():
                try:
                    return readme_path.read_text(encoding="utf-8", errors="ignore")
                except:
                    pass
        return None

    def get_project_context(self, repo_path: str) -> dict:
        """
        Extract project structure and key architectural files for AI analysis.
        Returns dict with file_tree and key_files (name: content)
        """
        path = Path(repo_path)
        if not path.exists():
            return {}

        context = {
            "file_tree": [],
            "key_files": {}
        }

        # Key architectural files to look for
        anchor_files = {
            "package.json", "requirements.txt", "pyproject.toml", 
            "docker-compose.yml", "Dockerfile", "main.py", "index.js",
            "app.py", "go.mod", "cargo.toml", "pom.xml", "makefile"
        }

        # Exclude patterns
        exclude_dirs = {".git", "node_modules", "__pycache__", "venv", "dist", "build", ".idea", ".vscode"}
        sensitive_patterns = {".env", ".key", ".pem", "secrets", "password", "token", "credentials", ".config", ".p12", ".pfx"}
        
        try:
            for root, dirs, files in os.walk(path):
                # Modify dirs in-place to skip excluded directories
                dirs[:] = [d for d in dirs if d not in exclude_dirs]
                
                rel_root = os.path.relpath(root, path)
                if rel_root == ".":
                    rel_root = ""
                
                for f in files:
                    file_name_lower = f.lower()
                    file_rel_path = os.path.join(rel_root, f)
                    
                    # Security: Skip sensitive files
                    if any(p in file_name_lower for p in sensitive_patterns):
                        continue
                        
                    context["file_tree"].append(file_rel_path)
                    
                    # Capture anchor file content
                    if file_name_lower in anchor_files:
                        file_path = Path(root) / f
                        try:
                            # Efficiency: Only capture first 5KB to prevent context bloat
                            # and ensure we aren't reading massive binary files
                            if file_path.stat().st_size > 1024 * 1024: # 1MB limit for safety
                                content = "[File too large for context extraction]"
                            else:
                                content = file_path.read_text(encoding="utf-8", errors="ignore")[:5000]
                            context["key_files"][file_rel_path] = content
                        except:
                            pass
        except Exception as e:
            logger.error(f"Error extracting context for {repo_path}: {e}")

        # Limit tree to first 200 files
        context["file_tree"] = context["file_tree"][:200]
        return context
    
    def open_in_explorer(self, repo_path: str):
        """Open repo folder in Windows Explorer"""
        try:
            import subprocess
            subprocess.Popen(["explorer", repo_path])
        except Exception as e:
            logger.error(f"Error opening explorer: {e}")
    
    def open_folder(self):
        """Open the repos folder in Windows Explorer"""
        try:
            import subprocess
            subprocess.Popen(["explorer", str(self.base_path)])
        except Exception as e:
            logger.error(f"Error opening explorer: {e}")


# Singleton instance
_repo_manager = None

def get_repo_manager() -> RepoManager:
    """Get or create the repo manager singleton"""
    global _repo_manager
    if _repo_manager is None:
        _repo_manager = RepoManager()
    return _repo_manager
