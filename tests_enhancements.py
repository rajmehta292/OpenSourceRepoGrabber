"""
Unit tests for new enhancements: Heuristic Audits, License Knowledge Base,
Good First Issues Finder, and Repository Metadata Tools.
"""
import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from github_api import get_github_client, CURATED_STARTER_REPOS, LICENSE_KNOWLEDGE_BASE
from ollama_client import get_ollama_client
from repo_manager import get_repo_manager
from contributor_guide import FIRST_PR_WORKFLOW, GIT_ESSENTIALS


class TestEnhancements(unittest.TestCase):
    def setUp(self):
        self.github = get_github_client()
        self.ollama = get_ollama_client()
        self.repo_manager = get_repo_manager()

    def test_curated_starter_repos(self):
        """Verify curated starter repos exist and have valid structure"""
        self.assertGreaterEqual(len(CURATED_STARTER_REPOS), 4)
        for repo in CURATED_STARTER_REPOS:
            self.assertIn("full_name", repo)
            self.assertIn("stargazers_count", repo)
            self.assertIn("license_spdx_id", repo)

    def test_license_knowledge_base(self):
        """Verify license knowledge base has core open source licenses"""
        kb = self.github.get_license_knowledge_base()
        self.assertIn("MIT", kb)
        self.assertIn("Apache-2.0", kb)
        self.assertIn("BSD-3-Clause", kb)
        self.assertTrue(kb["MIT"]["commercial_use"])
        self.assertIn("summary", kb["MIT"])

    def test_good_first_issues_search(self):
        """Verify beginner issue search returns valid repositories"""
        issues = self.github.search_good_first_issues(language="Python")
        self.assertIsInstance(issues, list)
        self.assertGreater(len(issues), 0)
        self.assertIn("full_name", issues[0])

    def test_heuristic_architectural_audit(self):
        """Verify heuristic architecture audit runs and produces structured markdown"""
        mock_context = {
            "file_tree": [
                "main.py",
                "api/routes.py",
                "models.py",
                "requirements.txt",
                "Dockerfile",
                ".github/workflows/ci.yml"
            ],
            "key_files": {
                "requirements.txt": "fastapi>=0.100.0\nuvicorn>=0.22.0\npydantic>=2.0",
                "main.py": "from fastapi import FastAPI\napp = FastAPI()"
            }
        }
        report = self.ollama.perform_heuristic_audit(mock_context)
        self.assertIn("Project Oracle Architectural Audit", report)
        self.assertIn("FastAPI", report)
        self.assertIn("Layered / MVC", report)
        self.assertIn("Strategic Architectural Roadmap", report)

    def test_heuristic_smart_tags(self):
        """Verify heuristic smart tags are generated without Ollama"""
        mock_context = {
            "file_tree": ["app.py", "requirements.txt", "Dockerfile"],
            "key_files": {"requirements.txt": "flask\nrequests"}
        }
        tags = self.ollama.suggest_smart_tags("Flask web service", mock_context)
        self.assertIsInstance(tags, list)
        self.assertIn("Flask", tags)
        self.assertIn("Dockerized", tags)

    def test_repo_file_tree_and_stats(self):
        """Verify local repo tree generation and size statistics"""
        current_dir = os.path.dirname(os.path.abspath(__file__))
        tree = self.repo_manager.get_repo_file_tree(current_dir)
        stats = self.repo_manager.get_repo_stats(current_dir)
        
        self.assertIsInstance(tree, list)
        self.assertGreater(len(tree), 0)
        self.assertGreater(stats["file_count"], 0)
        self.assertGreater(stats["size_mb"], 0.0)

    def test_contributor_workflow(self):
        """Verify contributor guide contains full 5-stage lifecycle"""
        self.assertEqual(len(FIRST_PR_WORKFLOW), 5)
        self.assertGreaterEqual(len(GIT_ESSENTIALS), 5)


if __name__ == "__main__":
    unittest.main()

