"""
Git repository cloner for OpenSource Repo Grabber
"""
import os
import shutil
import logging
from pathlib import Path
from typing import Optional
import subprocess

import config

logger = logging.getLogger(__name__)


class GitCloner:
    def __init__(self, clone_base_path: str = None):
        self.clone_base_path = Path(clone_base_path) if clone_base_path else config.DATA_DIR / "cloned_repos"
        self.clone_base_path.mkdir(parents=True, exist_ok=True)

    def clone_repo(self, repo_url: str, repo_name: str) -> Optional[Path]:
        """Clone a git repository to local folder"""
        try:
            target_path = self.clone_base_path / repo_name.replace("/", "_")

            # Check if already cloned
            if target_path.exists():
                # Try to update with git pull
                try:
                    subprocess.run(
                        ["git", "fetch", "origin"],
                        cwd=target_path,
                        capture_output=True,
                        timeout=60
                    )
                    subprocess.run(
                        ["git", "pull", "origin", "main"],
                        cwd=target_path,
                        capture_output=True,
                        timeout=60
                    )
                    logger.info(f"Updated repo: {repo_name}")
                    return target_path
                except Exception as e:
                    logger.debug(f"Could not update {repo_name}, will re-clone: {e}")
                    # Remove and re-clone
                    shutil.rmtree(target_path)

            # Clone the repository
            result = subprocess.run(
                ["git", "clone", "--depth", "1", repo_url, str(target_path)],
                capture_output=True,
                timeout=300  # 5 minute timeout
            )

            if result.returncode == 0:
                logger.info(f"Cloned repo: {repo_name}")
                return target_path
            else:
                logger.error(f"Failed to clone {repo_name}: {result.stderr.decode()}")
                return None

        except subprocess.TimeoutExpired:
            logger.error(f"Timeout cloning {repo_name}")
            if target_path.exists():
                shutil.rmtree(target_path, ignore_errors=True)
            return None
        except Exception as e:
            logger.error(f"Error cloning {repo_name}: {e}")
            return None

    def clone_all_repos(self, repos: list) -> dict:
        """Clone multiple repositories and return results"""
        results = {}
        for repo in repos:
            try:
                path = self.clone_repo(repo.clone_url, repo.full_name)
                results[repo.full_name] = path
            except Exception as e:
                logger.error(f"Error with {repo.full_name}: {e}")
                results[repo.full_name] = None
        return results

    def delete_repo(self, repo_name: str) -> bool:
        """Delete a cloned repository"""
        try:
            target_path = self.clone_base_path / repo_name.replace("/", "_")
            if target_path.exists():
                shutil.rmtree(target_path)
                logger.info(f"Deleted repo: {repo_name}")
                return True
        except Exception as e:
            logger.error(f"Error deleting {repo_name}: {e}")
        return False

    def get_repo_path(self, repo_name: str) -> Optional[Path]:
        """Get the path to a cloned repository"""
        target_path = self.clone_base_path / repo_name.replace("/", "_")
        return target_path if target_path.exists() else None

    def list_cloned_repos(self) -> list:
        """List all cloned repositories"""
        repos = []
        try:
            for item in self.clone_base_path.iterdir():
                if item.is_dir():
                    repos.append(item.name)
        except Exception as e:
            logger.error(f"Error listing repos: {e}")
        return repos

    def get_readme_from_clone(self, repo_name: str) -> Optional[str]:
        """Get README from cloned repository"""
        repo_path = self.get_repo_path(repo_name)
        if not repo_path:
            return None

        # Look for common README filenames
        readme_names = ["README.md", "README.rst", "README.txt", "README", "readme.md"]
        for name in readme_names:
            readme_path = repo_path / name
            if readme_path.exists():
                try:
                    return readme_path.read_text(encoding="utf-8", errors="ignore")
                except Exception as e:
                    logger.debug(f"Error reading README: {e}")
        return None


# Singleton
_cloner = None


def get_cloner() -> GitCloner:
    """Get cloner singleton"""
    global _cloner
    if _cloner is None:
        _cloner = GitCloner()
    return _cloner
