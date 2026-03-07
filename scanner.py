"""
Background scanner service for perpetual repository updates
"""
import threading
import logging
import time
from datetime import datetime
from typing import Callable, Optional
from queue import Queue

import config
from github_api import get_github_client, RateLimitError
from database import get_database
from git_cloner import get_cloner
from models import Repository, RepoCategory, ScanStatus

logger = logging.getLogger(__name__)


class ScannerService:
    def __init__(self, interval_minutes: int = 30):
        self.interval_minutes = interval_minutes
        self.status = ScanStatus.IDLE
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.event = threading.Event()
        self.update_queue: Queue = Queue()

        # Callbacks for GUI updates
        self.on_status_change: Optional[Callable] = None
        self.on_repo_update: Optional[Callable] = None
        self.on_error: Optional[Callable] = None
        self.on_scan_complete: Optional[Callable] = None

        self.github = get_github_client()
        self.db = get_database()
        self.cloner = get_cloner()

    def start(self):
        """Start the scanner service"""
        if self.running:
            return

        self.running = True
        self.status = ScanStatus.RUNNING
        self._notify_status()

        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()
        logger.info("Scanner service started")

    def stop(self):
        """Stop the scanner service"""
        self.running = False
        self.event.set()
        self.status = ScanStatus.IDLE
        self._notify_status()
        logger.info("Scanner service stopped")

    def pause(self):
        """Pause the scanner"""
        self.status = ScanStatus.PAUSED
        self._notify_status()
        logger.info("Scanner paused")

    def resume(self):
        """Resume the scanner"""
        if self.status == ScanStatus.PAUSED:
            self.status = ScanStatus.RUNNING
            self._notify_status()
            logger.info("Scanner resumed")

    def trigger_scan(self):
        """Manually trigger an immediate scan"""
        self.event.set()

    def set_interval(self, minutes: int):
        """Update the scan interval"""
        self.interval_minutes = minutes
        logger.info(f"Scan interval updated to {minutes} minutes")

    def _run_loop(self):
        """Main scanner loop"""
        while self.running:
            try:
                # Run the scan
                self._run_scan()

                # Wait for interval or event
                self.event.wait(timeout=self.interval_minutes * 60)
                self.event.clear()

            except Exception as e:
                logger.error(f"Scanner error: {e}")
                self.status = ScanStatus.ERROR
                self._notify_status()
                if self.on_error:
                    self.on_error(str(e))

    def _run_scan(self):
        """Execute a single scan cycle"""
        self.status = ScanStatus.RUNNING
        self._notify_status()

        logger.info("Starting repository scan...")
        start_time = time.time()

        # Scan all-time top repos
        self._scan_all_time_top()

        # Scan trending repos
        self._scan_trending()

        # Update stats
        elapsed = time.time() - start_time
        logger.info(f"Scan completed in {elapsed:.1f} seconds")

        self.status = ScanStatus.RUNNING
        self._notify_status()

        if self.on_scan_complete:
            stats = self.db.get_stats()
            self.on_scan_complete(stats)

    def _scan_all_time_top(self):
        """Scan and update all-time top repositories"""
        logger.info("Scanning all-time top repos...")

        try:
            repos = self.github.get_all_time_top_repos(config.LICENSES)
            logger.info(f"Found {len(repos)} all-time top repos")

            # Clear old all-time repos and save new ones
            self.db.clear_category(RepoCategory.ALL_TIME_TOP)

            for repo in repos:
                # Fetch additional details
                self._enrich_repository(repo)
                self.db.save_repository(repo)
                self._notify_repo_update(repo)

                # Small delay to be nice to the API
                time.sleep(0.2)

        except RateLimitError as e:
            logger.warning(f"Rate limited: {e}")
            if self.on_error:
                self.on_error(str(e))
        except Exception as e:
            logger.error(f"Error scanning all-time top repos: {e}")
            if self.on_error:
                self.on_error(str(e))

    def _scan_trending(self):
        """Scan and update trending repositories"""
        logger.info("Scanning trending repos...")

        try:
            repos = self.github.get_trending_repos(config.LICENSES)
            logger.info(f"Found {len(repos)} trending repos")

            # Clear old trending repos
            self.db.clear_category(RepoCategory.TRENDING)

            for repo in repos:
                self._enrich_repository(repo)
                self.db.save_repository(repo)
                self._notify_repo_update(repo)

                time.sleep(0.2)

        except RateLimitError as e:
            logger.warning(f"Rate limited: {e}")
            if self.on_error:
                self.on_error(str(e))
        except Exception as e:
            logger.error(f"Error scanning trending repos: {e}")
            if self.on_error:
                self.on_error(str(e))

    def _enrich_repository(self, repo: Repository):
        """Fetch additional details for a repository"""
        owner, name = repo.full_name.split("/")

        try:
            # Clone the repository to local folder
            clone_path = self.cloner.clone_repo(repo.clone_url, repo.full_name)
            if clone_path:
                logger.info(f"Cloned repo: {repo.full_name} to {clone_path}")
                # Try to get README from cloned repo
                local_readme = self.cloner.get_readme_from_clone(repo.full_name)
                if local_readme:
                    repo.readme_content = local_readme

            # Get releases
            releases = self.github.get_releases(owner, name)
            if releases:
                self.db.save_releases(repo.id, releases)

            # Get commits
            commits = self.github.get_commits(owner, name)
            if commits:
                self.db.save_commits(repo.id, commits)

            # Get contributors
            contributors = self.github.get_contributors(owner, name)
            if contributors:
                self.db.save_contributors(repo.id, contributors)

            # Update scan time
            repo.last_scanned = datetime.now()

        except Exception as e:
            logger.debug(f"Could not enrich {repo.full_name}: {e}")

    def _notify_status(self):
        """Notify status change callback"""
        if self.on_status_change:
            self.on_status_change(self.status)

    def _notify_repo_update(self, repo: Repository):
        """Notify repo update callback"""
        if self.on_repo_update:
            self.on_repo_update(repo)

    def get_rate_limit(self) -> dict:
        """Get current GitHub API rate limit"""
        return self.github.get_rate_limit_status()


# Singleton
_scanner = None


def get_scanner() -> ScannerService:
    """Get scanner singleton"""
    global _scanner
    if _scanner is None:
        _scanner = ScannerService()
    return _scanner
