import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from workbench.__main__ import cache_directory, parser


class CacheLocationTests(unittest.TestCase):
    def setUp(self):
        directory = self.enterContext(TemporaryDirectory())
        self.root = Path(directory)
        self.platform_directory = self.root / "profile-cache"
        self.legacy = self.root / ".workbench-cache"
        self.cache_path = self.enterContext(patch(
            "workbench.__main__.user_cache_path", return_value=self.platform_directory
        ))
        self.enterContext(patch("workbench.__main__.Path.cwd", return_value=self.root))

    def create_database(self, directory):
        directory.mkdir()
        (directory / "public.sqlite3").touch()

    def test_online_uses_platform_cache_even_when_legacy_exists(self):
        self.create_database(self.legacy)
        self.assertEqual(cache_directory(None, offline=False), self.platform_directory)
        self.cache_path.assert_called_once_with("repo-trail", appauthor=False)
        self.assertFalse(self.platform_directory.exists())

    def test_offline_reads_legacy_when_platform_cache_has_no_database(self):
        self.create_database(self.legacy)
        self.assertEqual(cache_directory(None, offline=True), self.legacy)

    def test_offline_prefers_platform_database_when_both_exist(self):
        self.create_database(self.legacy)
        self.create_database(self.platform_directory)
        self.assertEqual(cache_directory(None, offline=True), self.platform_directory)

    def test_explicit_cli_path_takes_priority(self):
        explicit = self.root / "explicit"
        parsed = parser().parse_args([
            "--offline", "--cache-dir", str(explicit), "contribution-draft",
            "--repo", "owner/repo", "--keywords", "docs",
        ])
        self.assertEqual(cache_directory(parsed.cache_dir, parsed.offline), explicit)
        self.cache_path.assert_not_called()
