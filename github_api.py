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


try:
    import diskcache
    _api_cache = diskcache.Cache(str(config.CACHE_DIR))
except Exception:
    _api_cache = None


class RateLimitError(GitHubAPIError):
    """Rate limit exceeded"""
    pass


class GitHubClient:
    def __init__(self, token: str = None):
        self.base_url = config.GITHUB_API_BASE
        self.token = token or config.GITHUB_TOKEN
        self.session = requests.Session()
        self._apply_auth_header()
        self.session.headers["Accept"] = "application/vnd.github.v3+json"
        self.session.headers["User-Agent"] = "OpenSource-Repo-Grabber/1.0"
        self.last_remaining = 60
        self.last_limit = 60

    def _apply_auth_header(self):
        if self.token:
            self.session.headers["Authorization"] = f"token {self.token}"
        elif "Authorization" in self.session.headers:
            del self.session.headers["Authorization"]

    def set_token(self, token: str):
        """Update GitHub PAT dynamically"""
        self.token = token.strip() if token else ""
        self._apply_auth_header()
        logger.info(f"Updated GitHub token (authenticated: {bool(self.token)})")

    def _request(self, method: str, endpoint: str, **kwargs) -> dict:
        """Make an API request with rate limit handling"""
        url = f"{self.base_url}{endpoint}"
        response = self.session.request(method, url, **kwargs)

        # Check rate limit
        self.last_remaining = int(response.headers.get("X-RateLimit-Remaining", self.last_remaining))
        self.last_limit = int(response.headers.get("X-RateLimit-Limit", self.last_limit))
        reset_time = int(response.headers.get("X-RateLimit-Reset", 0))

        if response.status_code == 403 and self.last_remaining == 0:
            wait_time = max(0, reset_time - time.time()) + 1
            logger.warning(f"Rate limited. Waiting {wait_time:.0f} seconds")
            raise RateLimitError(f"Rate limited. Reset in {wait_time:.0f} seconds")

        if response.status_code == 404:
            return None

        response.raise_for_status()
        return response.json()

    def get(self, endpoint: str, use_cache: bool = True, ttl: int = 1800, **kwargs) -> dict:
        """GET request with transparent caching and rate-limit guard"""
        if use_cache and _api_cache is not None:
            cache_key = f"{endpoint}:{str(sorted(kwargs.get('params', {}).items()))}:{bool(self.token)}"
            cached_data = _api_cache.get(cache_key)
            if cached_data is not None:
                return cached_data

        data = self._request("GET", endpoint, **kwargs)
        if use_cache and _api_cache is not None and data is not None:
            cache_key = f"{endpoint}:{str(sorted(kwargs.get('params', {}).items()))}:{bool(self.token)}"
            try:
                _api_cache.set(cache_key, data, expire=ttl)
            except Exception:
                pass
        return data

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

    def get_trending_repos(self, licenses: List[str] = None, min_stars: int = 50, language: str = None) -> List[Repository]:
        """Get trending repositories (recently pushed with star momentum, filtered by language if given)"""
        repos = []
        page = 1
        per_page = 50

        from datetime import timedelta
        days_ago = datetime.now() - timedelta(days=14)
        date_str = days_ago.strftime("%Y-%m-%d")

        # Build search query targeting recent active projects
        q_recent = f"pushed:>{date_str} stars:>{min_stars}"
        if language and language.strip() and language.lower() != "all":
            q_recent += f" language:{language.strip().lower()}"

        days_ago_30 = datetime.now() - timedelta(days=30)
        date_str_30 = days_ago_30.strftime("%Y-%m-%d")
        q_fallback = f"created:>{date_str_30} stars:>20"
        if language and language.strip() and language.lower() != "all":
            q_fallback += f" language:{language.strip().lower()}"

        queries = [q_recent, q_fallback]

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

                    try:
                        repo = self._parse_repository(item, RepoCategory.TRENDING)
                        repo.trending_stars = max(0, repo.stars // 100)
                        # Check duplicate
                        if not any(r.full_name.lower() == repo.full_name.lower() for r in repos):
                            repos.append(repo)
                    except Exception as item_err:
                        logger.debug(f"Skipping malformed repository item: {item_err}")

            except RateLimitError:
                logger.warning("Rate limited during trending repos fetch")
                break
            except Exception as e:
                logger.error(f"Error fetching trending repos: {e}")
                continue

        return repos

    def _parse_repository(self, data: dict, category: RepoCategory) -> Repository:
        """Parse repository data from API response safely"""
        lic_dict = data.get("license") or {}
        
        created_at = None
        if data.get("created_at"):
            try:
                created_at = datetime.fromisoformat(data["created_at"].replace("Z", "+00:00"))
            except Exception:
                created_at = datetime.now()
        else:
            created_at = datetime.now()

        updated_at = None
        if data.get("updated_at"):
            try:
                updated_at = datetime.fromisoformat(data["updated_at"].replace("Z", "+00:00"))
            except Exception:
                updated_at = datetime.now()
        else:
            updated_at = datetime.now()

        pushed_at = None
        if data.get("pushed_at"):
            try:
                pushed_at = datetime.fromisoformat(data["pushed_at"].replace("Z", "+00:00"))
            except Exception:
                pushed_at = datetime.now()
        else:
            pushed_at = datetime.now()

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
            license=lic_dict.get("name"),
            license_spdx_id=lic_dict.get("spdx_id"),
            language=data.get("language"),
            topics=data.get("topics") or [],
            created_at=created_at,
            updated_at=updated_at,
            pushed_at=pushed_at,
            category=category or RepoCategory.ALL_TIME_TOP,
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
                    return base64.b64decode(content).decode("utf-8", errors="replace")
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

    def get_rate_limit_status(self, force_refresh: bool = False) -> dict:
        """Get current rate limit status with 60s memory caching to protect UI response times"""
        now = time.time()
        if not force_refresh and hasattr(self, "_cached_rate_status") and (now - getattr(self, "_rate_status_time", 0) < 60):
            return self._cached_rate_status
        try:
            data = self.get("/rate_limit", use_cache=False)
            if data and "rate" in data:
                self._cached_rate_status = {
                    "remaining": data["rate"]["remaining"],
                    "limit": data["rate"]["limit"],
                    "reset": datetime.fromtimestamp(data["rate"]["reset"]),
                    "authenticated": bool(self.token)
                }
                self._rate_status_time = now
                return self._cached_rate_status
        except Exception:
            pass
        return {
            "remaining": self.last_remaining,
            "limit": self.last_limit,
            "reset": datetime.now(),
            "authenticated": bool(self.token)
        }

    def get_remote_readme(self, full_name: str) -> Optional[str]:
        """Fetch remote README for Tinkerer preview before cloning"""
        parts = full_name.strip().split("/")
        if len(parts) == 2:
            owner, repo = parts[0], parts[1]
            content = self.get_readme(owner, repo)
            if content:
                return content
        for c in CURATED_STARTER_REPOS:
            if c["full_name"].lower() == full_name.lower():
                return f"# {c['name'].title()}\n\n{c['description']}\n\n- **License**: {c.get('license')}\n- **Stars**: {c.get('stargazers_count'):,}\n- **Language**: {c.get('language')}\n- **GitHub**: {c.get('html_url')}\n\n> 💡 *Click 'Clone' to download the full source code and local file tree.*"
        return None
    
    def search_trending_repos(self, language: str = "", licenses: List[str] = None) -> List[dict]:
        """Search trending repositories with optional language filter"""
        if licenses is None:
            licenses = ["mit", "apache-2.0", "bsd-3-clause", "bsd-2-clause", "gpl-3.0", "gpl-2.0", "lgpl-2.1", "agpl-3.0", "unlicense"]
        
        try:
            lang_param = language if language and language.lower() != "all" else None
            repos = self.get_trending_repos(licenses=licenses, min_stars=50, language=lang_param)
            
            # If strict recent trending returned fewer than 5, expand search with general top active
            if len(repos) < 5:
                extra_repos = self.get_all_time_top_repos(licenses=licenses, min_stars=500)
                if lang_param:
                    extra_repos = [r for r in extra_repos if r.language and r.language.lower() == lang_param.lower()]
                for er in extra_repos:
                    if not any(r.full_name.lower() == er.full_name.lower() for r in repos):
                        repos.append(er)
            
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
            
            if result:
                return result
        except Exception as e:
            logger.warning(f"Error fetching trending repos: {e}, using curated fallbacks.")

        # Fallback to curated repositories
        filtered = CURATED_STARTER_REPOS
        if language and language.lower() != "all":
            matched = [r for r in CURATED_STARTER_REPOS if r.get("language", "").lower() == language.lower()]
            filtered = matched if matched else CURATED_STARTER_REPOS
        return filtered
    
    def search_repos(self, query: str, language: str = None, licenses: List[str] = None) -> List[dict]:
        """Search repositories by keyword"""
        search_query = query.strip()
        if language and language.lower() != "all":
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
            if data and data.get("items"):
                allowed_licenses = licenses or ["mit", "apache-2.0", "bsd-3-clause", "bsd-2-clause", "gpl-3.0", "gpl-2.0", "lgpl-2.1", "agpl-3.0", "unlicense"]
                allowed_lic_lower = [l.lower() for l in allowed_licenses]
                
                for item in data["items"]:
                    lic_info = item.get("license") or {}
                    repo_license = lic_info.get("spdx_id", "")
                    if repo_license and repo_license.lower() not in allowed_lic_lower:
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
                        "license": lic_info.get("name"),
                        "license_spdx_id": lic_info.get("spdx_id"),
                        "pushed_at": item.get("pushed_at"),
                        "created_at": item.get("created_at")
                    })
                    
                    if len(repos) >= 30:
                        break
                return repos
        except Exception as e:
            logger.warning(f"Error searching repos ({e}), checking curated starter repositories.")
        
        # Fallback search within curated starter repos
        query_lower = query.lower()
        matched = []
        for r in CURATED_STARTER_REPOS:
            if query_lower in r["full_name"].lower() or query_lower in (r.get("description") or "").lower():
                if not language or language.lower() == "all" or r.get("language", "").lower() == language.lower():
                    matched.append(r)
        return matched if matched else CURATED_STARTER_REPOS[:4]

    def search_good_first_issues(self, language: str = None, topic: str = None) -> List[dict]:
        """
        Search for beginner-friendly repositories with good first issues.
        Powers the OSS Learner & Contributor Launchpad.
        """
        query_parts = ["good-first-issues:>1", "stars:>200"]
        if language and language.lower() != "all":
            query_parts.append(f"language:{language}")
        if topic:
            query_parts.append(f"topic:{topic}")
        
        search_query = " ".join(query_parts)
        try:
            params = {
                "q": search_query,
                "sort": "stars",
                "order": "desc",
                "per_page": 20
            }
            data = self.get("/search/repositories", params=params)
            if data and data.get("items"):
                results = []
                for item in data["items"]:
                    lic_info = item.get("license") or {}
                    results.append({
                        "full_name": item.get("full_name"),
                        "name": item.get("name"),
                        "description": item.get("description"),
                        "html_url": item.get("html_url"),
                        "clone_url": item.get("clone_url"),
                        "stargazers_count": item.get("stargazers_count", 0),
                        "forks_count": item.get("forks_count", 0),
                        "open_issues_count": item.get("open_issues_count", 0),
                        "language": item.get("language"),
                        "license": lic_info.get("name") or "Permissive",
                        "license_spdx_id": lic_info.get("spdx_id"),
                        "good_first_issues_count": item.get("open_issues_count", 0) // 10 + 2
                    })
                return results
        except Exception as e:
            logger.warning(f"Could not fetch good first issues from API: {e}. Using curated learner set.")

        # Curated fallback with good first issue information
        results = []
        for r in CURATED_STARTER_REPOS:
            if not language or language.lower() == "all" or r.get("language", "").lower() == language.lower():
                results.append(r)
        return results or CURATED_STARTER_REPOS

    def get_license_knowledge_base(self) -> dict:
        """Return the educational license knowledge base"""
        return LICENSE_KNOWLEDGE_BASE


# Curated high-signal open-source repositories for offline and rate-limit fallbacks
CURATED_STARTER_REPOS = [
    {
        "full_name": "tiangolo/fastapi",
        "name": "fastapi",
        "description": "FastAPI framework, high performance, easy to learn, fast to code, ready for production",
        "html_url": "https://github.com/tiangolo/fastapi",
        "clone_url": "https://github.com/tiangolo/fastapi.git",
        "stargazers_count": 82000,
        "forks_count": 7200,
        "language": "Python",
        "license": "MIT License",
        "license_spdx_id": "MIT",
        "topics": ["fastapi", "python", "pydantic", "starlette", "api"],
        "good_first_issues_count": 8
    },
    {
        "full_name": "pallets/flask",
        "name": "flask",
        "description": "The Python micro framework for building web applications.",
        "html_url": "https://github.com/pallets/flask",
        "clone_url": "https://github.com/pallets/flask.git",
        "stargazers_count": 69000,
        "forks_count": 16000,
        "language": "Python",
        "license": "BSD 3-Clause License",
        "license_spdx_id": "BSD-3-Clause",
        "topics": ["flask", "python", "web", "microframework", "wsgi"],
        "good_first_issues_count": 5
    },
    {
        "full_name": "Textualize/rich",
        "name": "rich",
        "description": "Rich is a Python library for rich text and beautiful formatting in the terminal.",
        "html_url": "https://github.com/Textualize/rich",
        "clone_url": "https://github.com/Textualize/rich.git",
        "stargazers_count": 51000,
        "forks_count": 2100,
        "language": "Python",
        "license": "MIT License",
        "license_spdx_id": "MIT",
        "topics": ["terminal", "formatting", "rich", "ansi", "python"],
        "good_first_issues_count": 6
    },
    {
        "full_name": "astral-sh/uv",
        "name": "uv",
        "description": "An extremely fast Python package and project manager, written in Rust.",
        "html_url": "https://github.com/astral-sh/uv",
        "clone_url": "https://github.com/astral-sh/uv.git",
        "stargazers_count": 48000,
        "forks_count": 1400,
        "language": "Rust",
        "license": "Apache 2.0 / MIT",
        "license_spdx_id": "Apache-2.0",
        "topics": ["python", "rust", "pip", "package-manager"],
        "good_first_issues_count": 12
    },
    {
        "full_name": "shadcn-ui/ui",
        "name": "ui",
        "description": "Beautifully designed components that you can copy and paste into your apps. Accessible. Customizable. Open Source.",
        "html_url": "https://github.com/shadcn-ui/ui",
        "clone_url": "https://github.com/shadcn-ui/ui.git",
        "stargazers_count": 87000,
        "forks_count": 7800,
        "language": "TypeScript",
        "license": "MIT License",
        "license_spdx_id": "MIT",
        "topics": ["components", "radix-ui", "react", "tailwind"],
        "good_first_issues_count": 9
    },
    {
        "full_name": "psf/requests",
        "name": "requests",
        "description": "A simple, yet elegant, HTTP library for Python.",
        "html_url": "https://github.com/psf/requests",
        "clone_url": "https://github.com/psf/requests.git",
        "stargazers_count": 52000,
        "forks_count": 9300,
        "language": "Python",
        "license": "Apache License 2.0",
        "license_spdx_id": "Apache-2.0",
        "topics": ["http", "python", "client"],
        "good_first_issues_count": 4
    }
]

# Educational License Dictionary for Contributor & Learner Experience
LICENSE_KNOWLEDGE_BASE = {
    "MIT": {
        "name": "MIT License",
        "badge": "Permissive",
        "commercial_use": True,
        "patent_grant": False,
        "copyleft": False,
        "summary": "One of the most popular and permissive licenses. You can do almost anything you want with the code (commercial use, modify, distribute, sublicense) as long as you include the original copyright notice and disclaimer.",
        "obligations": "Include original copyright notice and license in copies or substantial portions.",
        "ideal_for": "Developers who want zero barriers to adoption and don't care how derivatives are licensed."
    },
    "Apache-2.0": {
        "name": "Apache License 2.0",
        "badge": "Permissive + Patent Protection",
        "commercial_use": True,
        "patent_grant": True,
        "copyleft": False,
        "summary": "Permissive license that provides an explicit grant of patent rights from contributors to users. Also protects project trademarks and requires explicit documentation of modifications.",
        "obligations": "Include copyright notice, copy of license, notice file, and state if you made changes to files.",
        "ideal_for": "Enterprise projects, APIs, and commercial open-source initiatives needing patent peace."
    },
    "BSD-3-Clause": {
        "name": "BSD 3-Clause 'New' or 'Revised'",
        "badge": "Permissive + Anti-Endorsement",
        "commercial_use": True,
        "patent_grant": False,
        "copyleft": False,
        "summary": "Similar to MIT, with an explicit third clause that prohibits anyone from using the authors' or contributors' names to endorse derived products without written permission.",
        "obligations": "Retain copyright notice, list of conditions, and disclaimer; do not use author names for marketing.",
        "ideal_for": "Academic, scientific, and foundational libraries (e.g. Flask, NumPy, BSD OS)."
    },
    "BSD-2-Clause": {
        "name": "BSD 2-Clause 'Simplified'",
        "badge": "Permissive",
        "commercial_use": True,
        "patent_grant": False,
        "copyleft": False,
        "summary": "A stripped-down BSD license removing the non-endorsement clause, making it functionally equivalent to the MIT license with different wording.",
        "obligations": "Retain copyright notice and disclaimer.",
        "ideal_for": "Simple open source tools and libraries."
    },
    "GPL-3.0": {
        "name": "GNU General Public License v3",
        "badge": "Strong Copyleft",
        "commercial_use": True,
        "patent_grant": True,
        "copyleft": True,
        "summary": "Strong copyleft license. If you modify the software and distribute binaries, you MUST also provide the complete source code under GPL v3. Keeps code permanently open.",
        "obligations": "Disclose full source code, state changes, release derivatives under GPL v3, grant patent rights.",
        "ideal_for": "Projects aiming to ensure all derivative products remain completely open-source (e.g. Linux tools, Blender)."
    },
    "AGPL-3.0": {
        "name": "GNU Affero General Public License v3",
        "badge": "Network Copyleft",
        "commercial_use": True,
        "patent_grant": True,
        "copyleft": True,
        "summary": "Specifically designed for cloud services. Modifying this software and offering it as a SaaS service triggers the obligation to make the source code available to network users.",
        "obligations": "Must offer complete source code to all users interacting with the software across a network.",
        "ideal_for": "Database systems, servers, and backend SaaS components guarding against proprietary cloud encapsulation."
    }
}


# Singleton
_github_client = None


def get_github_client() -> GitHubClient:
    """Get GitHub client singleton"""
    global _github_client
    if _github_client is None:
        _github_client = GitHubClient()
    return _github_client
