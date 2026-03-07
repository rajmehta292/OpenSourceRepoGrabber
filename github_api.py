"""
GitHub API client for fetching repository data
"""
import time
import logging
from typing import List, Optional, Tuple
from datetime import datetime

import requests

import config
from models import Repository, Release, Commit, Contributor, RepoCategory

logger = logging.getLogger(__name__)


class GitHubAPIError(Exception):
    """GitHub API error"""
    pass


class RateLimitError(GitHubAPIError):
    """Rate limit exceeded"""
    pass


class GitHubClient:
    def __init__(self, token: str = None):
        self.base_url = config.GITHUB_API_BASE
        self.token = token or config.GITHUB_TOKEN
        self.session = requests.Session()
        if self.token:
            self.session.headers["Authorization"] = f"token {self.token}"
        self.session.headers["Accept"] = "application/vnd.github.v3+json"
        self.session.headers["User-Agent"] = "OpenSource-Repo-Grabber/1.0"

    def _request(self, method: str, endpoint: str, **kwargs) -> dict:
        """Make an API request with rate limit handling"""
        url = f"{self.base_url}{endpoint}"
        response = self.session.request(method, url, **kwargs)

        # Check rate limit
        remaining = int(response.headers.get("X-RateLimit-Remaining", 60))
        reset_time = int(response.headers.get("X-RateLimit-Reset", 0))

        if response.status_code == 403 and remaining == 0:
            wait_time = max(0, reset_time - time.time()) + 1
            logger.warning(f"Rate limited. Waiting {wait_time:.0f} seconds")
            raise RateLimitError(f"Rate limited. Reset in {wait_time:.0f} seconds")

        if response.status_code == 404:
            return None

        response.raise_for_status()
        return response.json()

    def get(self, endpoint: str, **kwargs) -> dict:
        """GET request"""
        return self._request("GET", endpoint, **kwargs)

    def get_all_time_top_repos(self, licenses: List[str], min_stars: int = 1000) -> List[Repository]:
        """Get top all-time repositories by stars with specified licenses"""
        repos = []
        page = 1
        per_page = 100

        # Build license query
        license_query = " OR ".join([f"license:{l}" for l in licenses])

        while len(repos) < config.TOP_REPOS_COUNT:
            params = {
                "q": f"{license_query} stars:>{min_stars}",
                "sort": "stars",
                "order": "desc",
                "per_page": per_page,
                "page": page
            }

            try:
                data = self.get("/search/repositories", params=params)
                if not data or not data.get("items"):
                    break

                for item in data["items"]:
                    if len(repos) >= config.TOP_REPOS_COUNT:
                        break

                    repo = self._parse_repository(item, RepoCategory.ALL_TIME_TOP)
                    if repo.license_spdx_id in licenses:
                        repos.append(repo)

                page += 1

                # Be nice to the API
                time.sleep(0.5)

            except RateLimitError:
                logger.warning("Rate limited during top repos fetch")
                break
            except Exception as e:
                logger.error(f"Error fetching top repos: {e}")
                break

        return repos

    def get_trending_repos(self, licenses: List[str], min_stars: int = 100) -> List[Repository]:
        """Get trending repositories (created in last 30 days or recently pushed)"""
        repos = []
        page = 1
        per_page = 100

        from datetime import timedelta
        # Use 7 days ago for more relevant trending
        days_ago = datetime.now() - timedelta(days=7)
        date_str = days_ago.strftime("%Y-%m-%d")

        # Simplified query without license filter first
        queries = [
            f"pushed:>{date_str} stars:>500",
            f"created:>{date_str} stars:>100",
        ]

        for query in queries:
            if len(repos) >= config.TRENDING_REPOS_COUNT:
                break

            params = {
                "q": query,
                "sort": "stars",
                "order": "desc",
                "per_page": per_page,
                "page": page
            }

            try:
                data = self.get("/search/repositories", params=params)
                if not data or not data.get("items"):
                    continue

                for item in data["items"]:
                    if len(repos) >= config.TRENDING_REPOS_COUNT:
                        break

                    repo = self._parse_repository(item, RepoCategory.TRENDING)
                    repo.trending_stars = max(0, repo.stars // 100)
                    repos.append(repo)

                time.sleep(0.5)

            except RateLimitError:
                logger.warning("Rate limited during trending repos fetch")
                break
            except Exception as e:
                logger.error(f"Error fetching trending repos: {e}")
                continue

        return repos

    def _parse_repository(self, data: dict, category: RepoCategory) -> Repository:
        """Parse repository data from API response"""
        return Repository(
            id=data["id"],
            name=data["name"],
            full_name=data["full_name"],
            description=data.get("description"),
            html_url=data["html_url"],
            clone_url=data.get("clone_url", ""),
            stars=data.get("stargazers_count", 0),
            forks=data.get("forks_count", 0),
            watchers=data.get("watchers_count", 0),
            open_issues=data.get("open_issues_count", 0),
            license=data.get("license", {}).get("name"),
            license_spdx_id=data.get("license", {}).get("spdx_id"),
            language=data.get("language"),
            topics=data.get("topics", []),
            created_at=datetime.fromisoformat(data["created_at"].replace("Z", "+00:00")),
            updated_at=datetime.fromisoformat(data["updated_at"].replace("Z", "+00:00")),
            pushed_at=datetime.fromisoformat(data["pushed_at"].replace("Z", "+00:00")),
            category=category,
            last_scanned=datetime.now()
        )

    def get_readme(self, owner: str, repo: str) -> Optional[str]:
        """Get repository README content"""
        try:
            # Try to get README
            data = self.get(f"/repos/{owner}/{repo}/readme")
            if data:
                import base64
                content = data.get("content", "")
                if content:
                    return base64.b64decode(content).decode("utf-8")
        except Exception as e:
            logger.debug(f"Could not fetch README for {owner}/{repo}: {e}")
        return None

    def get_releases(self, owner: str, repo: str) -> List[Release]:
        """Get repository releases"""
        try:
            data = self.get(f"/repos/{owner}/{repo}/releases", per_page=10)
            if not data:
                return []

            releases = []
            for item in data:
                release = Release(
                    id=item["id"],
                    name=item.get("name", ""),
                    tag_name=item["tag_name"],
                    draft=item.get("draft", False),
                    prerelease=item.get("prerelease", False),
                    created_at=datetime.fromisoformat(item["created_at"].replace("Z", "+00:00")),
                    published_at=datetime.fromisoformat(item["published_at"].replace("Z", "+00:00")) if item.get("published_at") else None,
                    html_url=item["html_url"],
                    body=item.get("body")
                )
                releases.append(release)

            return releases

        except Exception as e:
            logger.debug(f"Could not fetch releases for {owner}/{repo}: {e}")
            return []

    def get_commits(self, owner: str, repo: str, limit: int = 10) -> List[Commit]:
        """Get recent commits"""
        try:
            data = self.get(f"/repos/{owner}/{repo}/commits", per_page=limit)
            if not data:
                return []

            commits = []
            for item in data:
                commit = Commit(
                    sha=item["sha"],
                    message=item["commit"]["message"],
                    author=item["commit"]["author"]["name"],
                    author_login=item.get("author", {}).get("login"),
                    date=datetime.fromisoformat(item["commit"]["author"]["date"].replace("Z", "+00:00")),
                    html_url=item["html_url"]
                )
                commits.append(commit)

            return commits

        except Exception as e:
            logger.debug(f"Could not fetch commits for {owner}/{repo}: {e}")
            return []

    def get_contributors(self, owner: str, repo: str, limit: int = 10) -> List[Contributor]:
        """Get top contributors"""
        try:
            data = self.get(f"/repos/{owner}/{repo}/contributors", per_page=limit)
            if not data:
                return []

            contributors = []
            for item in data:
                contrib = Contributor(
                    id=item["id"],
                    login=item["login"],
                    avatar_url=item["avatar_url"],
                    contributions=item["contributions"],
                    html_url=item["html_url"]
                )
                contributors.append(contrib)

            return contributors

        except Exception as e:
            logger.debug(f"Could not fetch contributors for {owner}/{repo}: {e}")
            return []

    def get_rate_limit_status(self) -> dict:
        """Get current rate limit status"""
        try:
            data = self.get("/rate_limit")
            return {
                "remaining": data["rate"]["remaining"],
                "limit": data["rate"]["limit"],
                "reset": datetime.fromtimestamp(data["rate"]["reset"])
            }
        except Exception:
            return {"remaining": 60, "limit": 60, "reset": datetime.now()}
    
    def search_trending_repos(self, language: str = "", licenses: List[str] = None) -> List[dict]:
        """Search trending repositories with optional language filter"""
        if licenses is None:
            licenses = ["mit", "apache-2.0", "bsd-3-clause", "bsd-2-clause", "gpl-3.0", "gpl-2.0", "lgpl-2.1", "agpl-3.0", "unlicense"]
        
        repos = self.get_trending_repos(licenses=licenses, min_stars=100)
        
        # Filter by language if specified
        if language:
            repos = [r for r in repos if r.language and r.language.lower() == language.lower()]
        
        # Convert to dict format for GUI
        result = []
        for repo in repos:
            result.append({
                "full_name": repo.full_name,
                "name": repo.name,
                "description": repo.description,
                "html_url": repo.html_url,
                "clone_url": repo.clone_url,
                "stargazers_count": repo.stars,
                "forks_count": repo.forks,
                "language": repo.language,
                "license": repo.license,
                "license_spdx_id": repo.license_spdx_id,
                "pushed_at": repo.pushed_at,
                "created_at": repo.created_at
            })
        
        return result
    
    def search_repos(self, query: str, language: str = None, licenses: List[str] = None) -> List[dict]:
        """Search repositories by keyword"""
        # Build simple search query
        search_query = query
        if language:
            search_query += f" language:{language}"
        
        repos = []
        page = 1
        per_page = 30
        
        try:
            params = {
                "q": search_query,
                "sort": "stars",
                "order": "desc",
                "per_page": per_page,
                "page": page
            }
            
            data = self.get("/search/repositories", params=params)
            if not data or not data.get("items"):
                return []
            
            # Filter allowed licenses
            allowed_licenses = licenses or ["mit", "apache-2.0", "bsd-3-clause", "bsd-2-clause", "gpl-3.0", "gpl-2.0", "lgpl-2.1", "agpl-3.0", "unlicense"]
            
            for item in data["items"]:
                repo_license = item.get("license", {}).get("spdx_id", "")
                if repo_license and repo_license.lower() not in [l.lower() for l in allowed_licenses]:
                    continue
                    
                repos.append({
                    "full_name": item.get("full_name"),
                    "name": item.get("name"),
                    "description": item.get("description"),
                    "html_url": item.get("html_url"),
                    "clone_url": item.get("clone_url"),
                    "stargazers_count": item.get("stargazers_count", 0),
                    "forks_count": item.get("forks_count", 0),
                    "language": item.get("language"),
                    "license": item.get("license", {}).get("name"),
                    "license_spdx_id": item.get("license", {}).get("spdx_id"),
                    "pushed_at": item.get("pushed_at"),
                    "created_at": item.get("created_at")
                })
                
                if len(repos) >= 30:
                    break
        
        except Exception as e:
            logger.error(f"Error searching repos: {e}")
        
        return repos


# Singleton
_github_client = None


def get_github_client() -> GitHubClient:
    """Get GitHub client singleton"""
    global _github_client
    if _github_client is None:
        _github_client = GitHubClient()
    return _github_client
