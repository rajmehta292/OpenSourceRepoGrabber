"""
Data models for OpenSource Repo Grabber
"""
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum


class LicenseType(str, Enum):
    MIT = "mit"
    APACHE_2_0 = "apache-2.0"
    BSD_3_CLAUSE = "bsd-3-clause"
    BSD_2_CLAUSE = "bsd-2-clause"


class RepoCategory(str, Enum):
    ALL_TIME_TOP = "all_time_top"
    TRENDING = "trending"


class Repository(BaseModel):
    """Main repository model"""
    id: int
    name: str
    full_name: str
    description: Optional[str] = None
    html_url: str
    clone_url: str
    stars: int = 0
    forks: int = 0
    watchers: int = 0
    open_issues: int = 0
    license: Optional[str] = None
    license_spdx_id: Optional[str] = None
    language: Optional[str] = None
    topics: List[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
    pushed_at: datetime
    category: RepoCategory
    last_scanned: datetime = Field(default_factory=datetime.now)
    readme_content: Optional[str] = None
    architectural_audit: Optional[str] = None
    smart_tags: List[str] = Field(default_factory=list)
    trending_stars: int = 0  # Stars gained this week for trending repos


class Release(BaseModel):
    """Release/tag model"""
    id: int
    name: str
    tag_name: str
    draft: bool = False
    prerelease: bool = False
    created_at: datetime
    published_at: Optional[datetime] = None
    html_url: str
    body: Optional[str] = None


class Commit(BaseModel):
    """Commit model"""
    sha: str
    message: str
    author: str
    author_login: Optional[str] = None
    date: datetime
    html_url: str


class Contributor(BaseModel):
    """Contributor model"""
    id: int
    login: str
    avatar_url: str
    contributions: int
    html_url: str


class RepositoryDetail(BaseModel):
    """Extended repository details"""
    repo: Repository
    releases: List[Release] = Field(default_factory=list)
    recent_commits: List[Commit] = Field(default_factory=list)
    contributors: List[Contributor] = Field(default_factory=list)


class ScanStatus(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    ERROR = "error"


class AppSettings(BaseModel):
    """Application settings"""
    scan_interval: int = 30  # minutes
    ollama_model: str = "llama3.2"
    ollama_url: str = "http://localhost:11434"
    theme: str = "dark"
    auto_scan: bool = True
