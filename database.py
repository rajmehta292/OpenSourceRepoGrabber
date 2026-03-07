"""
Database operations for OpenSource Repo Grabber
"""
import sqlite3
from typing import List, Optional, Tuple
from datetime import datetime
from contextlib import contextmanager

import config
from models import Repository, Release, Commit, Contributor, RepoCategory


class Database:
    def __init__(self, db_path: str = None):
        self.db_path = db_path or str(config.DB_PATH)
        self._init_db()

    @contextmanager
    def _get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_db(self):
        """Initialize database schema"""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Repositories table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS repositories (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    full_name TEXT UNIQUE NOT NULL,
                    description TEXT,
                    html_url TEXT NOT NULL,
                    clone_url TEXT,
                    stars INTEGER DEFAULT 0,
                    forks INTEGER DEFAULT 0,
                    watchers INTEGER DEFAULT 0,
                    open_issues INTEGER DEFAULT 0,
                    license TEXT,
                    license_spdx_id TEXT,
                    language TEXT,
                    topics TEXT,
                    created_at TEXT,
                    updated_at TEXT,
                    pushed_at TEXT,
                    category TEXT NOT NULL,
                    last_scanned TEXT,
                    readme_content TEXT,
                    trending_stars INTEGER DEFAULT 0
                )
            """)

            # Releases table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS releases (
                    id INTEGER PRIMARY KEY,
                    repo_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    tag_name TEXT NOT NULL,
                    draft INTEGER DEFAULT 0,
                    prerelease INTEGER DEFAULT 0,
                    created_at TEXT,
                    published_at TEXT,
                    html_url TEXT,
                    body TEXT,
                    FOREIGN KEY (repo_id) REFERENCES repositories(id)
                )
            """)

            # Commits table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS commits (
                    id INTEGER PRIMARY KEY,
                    repo_id INTEGER NOT NULL,
                    sha TEXT NOT NULL,
                    message TEXT,
                    author TEXT,
                    author_login TEXT,
                    date TEXT,
                    html_url TEXT,
                    FOREIGN KEY (repo_id) REFERENCES repositories(id)
                )
            """)

            # Contributors table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS contributors (
                    id INTEGER PRIMARY KEY,
                    repo_id INTEGER NOT NULL,
                    login TEXT NOT NULL,
                    avatar_url TEXT,
                    contributions INTEGER DEFAULT 0,
                    html_url TEXT,
                    FOREIGN KEY (repo_id) REFERENCES repositories(id)
                )
            """)

            # Settings table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            """)

            # Create indexes
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_repos_category 
                ON repositories(category)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_repos_stars 
                ON repositories(stars DESC)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_repos_license 
                ON repositories(license_spdx_id)
            """)

    def save_repository(self, repo: Repository) -> bool:
        """Save or update a repository"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            topics_str = ",".join(repo.topics) if repo.topics else ""

            cursor.execute("""
                INSERT OR REPLACE INTO repositories (
                    id, name, full_name, description, html_url, clone_url,
                    stars, forks, watchers, open_issues, license,
                    license_spdx_id, language, topics, created_at,
                    updated_at, pushed_at, category, last_scanned,
                    readme_content, trending_stars
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                repo.id, repo.name, repo.full_name, repo.description,
                repo.html_url, repo.clone_url, repo.stars, repo.forks,
                repo.watchers, repo.open_issues, repo.license,
                repo.license_spdx_id, repo.language, topics_str,
                repo.created_at.isoformat(), repo.updated_at.isoformat(),
                repo.pushed_at.isoformat(), repo.category.value,
                repo.last_scanned.isoformat(), repo.readme_content,
                repo.trending_stars
            ))
            return True

    def get_repositories(self, category: Optional[RepoCategory] = None,
                         license: Optional[str] = None,
                         limit: int = 100) -> List[Repository]:
        """Get repositories with optional filters"""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            query = "SELECT * FROM repositories WHERE 1=1"
            params = []

            if category:
                query += " AND category = ?"
                params.append(category.value)

            if license:
                query += " AND license_spdx_id = ?"
                params.append(license)

            query += " ORDER BY stars DESC LIMIT ?"
            params.append(limit)

            cursor.execute(query, params)
            rows = cursor.fetchall()

            repos = []
            for row in rows:
                topics = row['topics'].split(",") if row['topics'] else []
                topics = [t for t in topics if t]

                repo = Repository(
                    id=row['id'],
                    name=row['name'],
                    full_name=row['full_name'],
                    description=row['description'],
                    html_url=row['html_url'],
                    clone_url=row['clone_url'] or "",
                    stars=row['stars'],
                    forks=row['forks'],
                    watchers=row['watchers'],
                    open_issues=row['open_issues'],
                    license=row['license'],
                    license_spdx_id=row['license_spdx_id'],
                    language=row['language'],
                    topics=topics,
                    created_at=datetime.fromisoformat(row['created_at']),
                    updated_at=datetime.fromisoformat(row['updated_at']),
                    pushed_at=datetime.fromisoformat(row['pushed_at']),
                    category=RepoCategory(row['category']),
                    last_scanned=datetime.fromisoformat(row['last_scanned']),
                    readme_content=row['readme_content'],
                    trending_stars=row['trending_stars']
                )
                repos.append(repo)

            return repos

    def get_repository(self, repo_id: int = None, full_name: str = None) -> Optional[Repository]:
        """Get a single repository by ID or full name"""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            if repo_id:
                cursor.execute("SELECT * FROM repositories WHERE id = ?", (repo_id,))
            elif full_name:
                cursor.execute("SELECT * FROM repositories WHERE full_name = ?", (full_name,))
            else:
                return None

            row = cursor.fetchone()
            if not row:
                return None

            topics = row['topics'].split(",") if row['topics'] else []
            topics = [t for t in topics if t]

            return Repository(
                id=row['id'],
                name=row['name'],
                full_name=row['full_name'],
                description=row['description'],
                html_url=row['html_url'],
                clone_url=row['clone_url'] or "",
                stars=row['stars'],
                forks=row['forks'],
                watchers=row['watchers'],
                open_issues=row['open_issues'],
                license=row['license'],
                license_spdx_id=row['license_spdx_id'],
                language=row['language'],
                topics=topics,
                created_at=datetime.fromisoformat(row['created_at']),
                updated_at=datetime.fromisoformat(row['updated_at']),
                pushed_at=datetime.fromisoformat(row['pushed_at']),
                category=RepoCategory(row['category']),
                last_scanned=datetime.fromisoformat(row['last_scanned']),
                readme_content=row['readme_content'],
                trending_stars=row['trending_stars']
            )

    def save_releases(self, repo_id: int, releases: List[Release]):
        """Save releases for a repository"""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Delete old releases
            cursor.execute("DELETE FROM releases WHERE repo_id = ?", (repo_id,))

            # Insert new releases
            for release in releases:
                cursor.execute("""
                    INSERT INTO releases (
                        repo_id, id, name, tag_name, draft, prerelease,
                        created_at, published_at, html_url, body
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    repo_id, release.id, release.name, release.tag_name,
                    int(release.draft), int(release.prerelease),
                    release.created_at.isoformat() if release.created_at else None,
                    release.published_at.isoformat() if release.published_at else None,
                    release.html_url, release.body
                ))

    def get_releases(self, repo_id: int) -> List[Release]:
        """Get releases for a repository"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM releases 
                WHERE repo_id = ? 
                ORDER BY published_at DESC
            """, (repo_id,))

            rows = cursor.fetchall()
            releases = []
            for row in rows:
                release = Release(
                    id=row['id'],
                    name=row['name'],
                    tag_name=row['tag_name'],
                    draft=bool(row['draft']),
                    prerelease=bool(row['prerelease']),
                    created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else datetime.now(),
                    published_at=datetime.fromisoformat(row['published_at']) if row['published_at'] else None,
                    html_url=row['html_url'],
                    body=row['body']
                )
                releases.append(release)
            return releases

    def save_commits(self, repo_id: int, commits: List[Commit]):
        """Save commits for a repository"""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("DELETE FROM commits WHERE repo_id = ?", (repo_id,))

            for commit in commits:
                cursor.execute("""
                    INSERT INTO commits (
                        repo_id, sha, message, author, author_login, date, html_url
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    repo_id, commit.sha, commit.message, commit.author,
                    commit.author_login, commit.date.isoformat(), commit.html_url
                ))

    def get_commits(self, repo_id: int, limit: int = 10) -> List[Commit]:
        """Get recent commits for a repository"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM commits 
                WHERE repo_id = ? 
                ORDER BY date DESC LIMIT ?
            """, (repo_id, limit))

            rows = cursor.fetchall()
            commits = []
            for row in rows:
                commit = Commit(
                    sha=row['sha'],
                    message=row['message'],
                    author=row['author'],
                    author_login=row['author_login'],
                    date=datetime.fromisoformat(row['date']),
                    html_url=row['html_url']
                )
                commits.append(commit)
            return commits

    def save_contributors(self, repo_id: int, contributors: List[Contributor]):
        """Save contributors for a repository"""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("DELETE FROM contributors WHERE repo_id = ?", (repo_id,))

            for contrib in contributors:
                cursor.execute("""
                    INSERT INTO contributors (
                        repo_id, id, login, avatar_url, contributions, html_url
                    ) VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    repo_id, contrib.id, contrib.login, contrib.avatar_url,
                    contrib.contributions, contrib.html_url
                ))

    def get_contributors(self, repo_id: int) -> List[Contributor]:
        """Get contributors for a repository"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM contributors 
                WHERE repo_id = ? 
                ORDER BY contributions DESC
            """, (repo_id,))

            rows = cursor.fetchall()
            contributors = []
            for row in rows:
                contrib = Contributor(
                    id=row['id'],
                    login=row['login'],
                    avatar_url=row['avatar_url'],
                    contributions=row['contributions'],
                    html_url=row['html_url']
                )
                contributors.append(contrib)
            return contributors

    def get_stats(self) -> dict:
        """Get database statistics"""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT COUNT(*) as total FROM repositories")
            total = cursor.fetchone()['total']

            cursor.execute("SELECT COUNT(*) as total FROM repositories WHERE category = 'all_time_top'")
            all_time = cursor.fetchone()['total']

            cursor.execute("SELECT COUNT(*) as total FROM repositories WHERE category = 'trending'")
            trending = cursor.fetchone()['total']

            cursor.execute("SELECT SUM(stars) as total FROM repositories")
            total_stars = cursor.fetchone()['total'] or 0

            cursor.execute("SELECT MAX(last_scanned) as last_scan FROM repositories")
            last_scan = cursor.fetchone()['last_scan']

            return {
                "total_repos": total,
                "all_time_top": all_time,
                "trending": trending,
                "total_stars": total_stars,
                "last_scan": datetime.fromisoformat(last_scan) if last_scan else None
            }

    def get_setting(self, key: str, default: str = None) -> Optional[str]:
        """Get a setting value"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
            row = cursor.fetchone()
            return row['value'] if row else default

    def set_setting(self, key: str, value: str):
        """Set a setting value"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)
            """, (key, value))

    def clear_category(self, category: RepoCategory):
        """Clear all repositories in a category"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM repositories WHERE category = ?", (category.value,))


# Singleton instance
_db = None


def get_database() -> Database:
    """Get the database singleton"""
    global _db
    if _db is None:
        _db = Database()
    return _db
