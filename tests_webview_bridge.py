"""Unit tests for the pywebview JSON API bridge (webview_app.OSRGApi)."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from webview_app import FRONTEND_DIST_DIR, OSRGApi


class TestWebViewBridge(unittest.TestCase):
    def setUp(self):
        self.api = OSRGApi()

    def test_frontend_bundle_built(self):
        self.assertTrue((FRONTEND_DIST_DIR / "index.html").exists())

    def test_ping_json_serializable(self):
        res = self.api.ping()
        self.assertTrue(res["ok"])
        json.dumps(res)

    def test_license_and_contributor_endpoints(self):
        lic = self.api.get_license_knowledge_base()
        self.assertTrue(lic["ok"])
        self.assertIn("MIT", lic["licenses"])

        guide = self.api.get_contributor_guide()
        self.assertTrue(guide["ok"])
        self.assertGreater(len(guide["workflow"]), 0)
        self.assertGreater(len(guide["git_essentials"]), 0)
        json.dumps(lic)
        json.dumps(guide)

    def test_read_local_file_safety_and_binary(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_dir = Path(tmpdir) / "sample-repo"
            repo_dir.mkdir()
            (repo_dir / "hello.py").write_text("print('hi')\n", encoding="utf-8")
            (repo_dir / "bin.dat").write_bytes(b"\x00\x01\x02\x03")

            ok_res = self.api.read_local_file(str(repo_dir), "hello.py")
            self.assertTrue(ok_res["ok"])
            self.assertIn("print('hi')", ok_res["content"])

            bin_res = self.api.read_local_file(str(repo_dir), "bin.dat")
            self.assertFalse(bin_res["ok"])
            self.assertIn("Binary", bin_res["error"])

            outside = self.api.read_local_file(str(repo_dir), "../outside.txt")
            self.assertFalse(outside["ok"])
            self.assertIn("Access denied", outside["error"])

    def test_open_external_url_scheme_guard(self):
        bad = self.api.open_external_url("javascript:alert(1)")
        self.assertFalse(bad["ok"])
        file_bad = self.api.open_external_url("file:///C:/Windows/win.ini")
        self.assertFalse(file_bad["ok"])

        with patch("webview_app.webbrowser.open") as mock_open:
            good = self.api.open_external_url("https://github.com/fastapi/fastapi")
            self.assertTrue(good["ok"])
            mock_open.assert_called_once_with("https://github.com/fastapi/fastapi")

    def test_overview_and_settings_json_serializable(self):
        ov = self.api.get_overview_data()
        self.assertTrue(ov["ok"])
        json.dumps(ov)

        st = self.api.get_settings()
        self.assertTrue(st["ok"])
        json.dumps(st)

    def test_trending_search_and_gfi_json_serializable(self):
        from datetime import datetime

        sample_repo = {
            "name": "fastapi",
            "full_name": "fastapi/fastapi",
            "description": "FastAPI framework",
            "html_url": "https://github.com/fastapi/fastapi",
            "clone_url": "https://github.com/fastapi/fastapi.git",
            "stars": 80000,
            "forks": 7000,
            "license_spdx_id": "MIT",
            "language": "Python",
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }
        with patch("webview_app.get_github_client") as mock_gh:
            client = mock_gh.return_value
            client.search_trending_repos.return_value = [sample_repo]
            client.search_repos.return_value = [sample_repo]
            client.search_good_first_issues.return_value = [
                {"title": "Fix typo", "repo": "fastapi/fastapi", "number": 1, "created_at": datetime.now()}
            ]
            client.get_rate_limit_status.return_value = {
                "limit": 60, "remaining": 59, "used": 1, "reset": datetime.now(), "authenticated": False
            }

            t_res = self.api.search_trending_repos("")
            self.assertTrue(t_res["ok"])
            json.dumps(t_res)

            s_res = self.api.search_repos("fastapi")
            self.assertTrue(s_res["ok"])
            json.dumps(s_res)

            g_res = self.api.search_good_first_issues("Python")
            self.assertTrue(g_res["ok"])
            json.dumps(g_res)


if __name__ == "__main__":
    unittest.main()
