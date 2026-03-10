import sys
import os
import shutil
from pathlib import Path
import unittest

# Add parent dir to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from repo_manager import get_repo_manager
from database import get_database
from models import Repository, RepoCategory
from datetime import datetime

class TestProjectOracle(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Setup a dummy repo for testing context extraction
        cls.test_repo_path = Path("tmp_test_repo")
        cls.test_repo_path.mkdir(exist_ok=True)
        (cls.test_repo_path / "package.json").write_text('{"name": "test-project"}')
        (cls.test_repo_path / "src").mkdir(exist_ok=True)
        (cls.test_repo_path / "src" / "main.py").write_text("print('hello')")
        (cls.test_repo_path / ".git").mkdir(exist_ok=True) # Should be ignored
        
    @classmethod
    def tearDownClass(cls):
        if cls.test_repo_path.exists():
            shutil.rmtree(cls.test_repo_path)

    def test_context_extraction(self):
        rm = get_repo_manager()
        context = rm.get_project_context(str(self.test_repo_path))
        
        self.assertIn("file_tree", context)
        self.assertIn("key_files", context)
        
        # Check if package.json is in key_files
        # The path in context is relative
        self.assertTrue(any("package.json" in k for k in context["key_files"]))
        
        # Check if .git is ignored in file_tree
        for f in context["file_tree"]:
            self.assertNotIn(".git", f)

    def test_database_persistence(self):
        db = get_database()
        
        # Create a dummy repo model
        repo = Repository(
            id=999999,
            name="test_repo",
            full_name="test/test_repo",
            html_url="https://github.com/test/test_repo",
            clone_url="https://github.com/test/test_repo.git",
            category=RepoCategory.ALL_TIME_TOP,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            pushed_at=datetime.now(),
            smart_tags=["Tag1", "Tag2"],
            architectural_audit="This is a test audit report."
        )
        
        # Save
        db.save_repository(repo)
        
        # Load
        loaded = db.get_repository(repo_id=999999)
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.smart_tags, ["Tag1", "Tag2"])
        self.assertEqual(loaded.architectural_audit, "This is a test audit report.")

if __name__ == "__main__":
    unittest.main()
