import unittest
from types import SimpleNamespace
from urllib.parse import parse_qs, urlsplit

from workbench.github import WorkbenchError
from workbench.submission import prepare_handoff

BASE = "a" * 40
HEAD = "b" * 40
SPEC = {
    "title": "Correct the installation link",
    "impact": "Readers cannot open the install guide.",
    "expected_behavior": "The link takes readers to the installation guide.",
    "actual_behavior": "The link opens a missing path.",
    "edits": [{"path": "README.md"}],
}
EVIDENCE = ("docs/install.md", 3, "README.md", 12)


class Snapshot:
    sha = BASE
    repo = "example/library"
    endpoint = "/repos/example/library"
    commit_link = f"https://github.com/{repo}/commit/{sha}"

    def __init__(self, templates=()):
        self.templates = templates

    def link(self, path, line):
        return f"https://github.com/{self.repo}/blob/{self.sha}/{path}#L{line}"

    def policy_paths(self):
        return self.templates


class API:
    def __init__(self, result):
        self.result = result
        self.calls = []

    def get(self, path, params=None, *, ttl):
        self.calls.append(path)
        return self.result


class SubmissionTests(unittest.TestCase):
    def test_issue_links_to_verified_evidence_and_prefills_exact_public_body(self):
        api = API({"has_issues": True})
        handoff = prepare_handoff(api, Snapshot(), SimpleNamespace(publish="issue"), SPEC, EVIDENCE, None, [])
        fields = parse_qs(urlsplit(handoff.chrome_url()).query)
        self.assertEqual(fields["title"], [SPEC["title"]])
        self.assertIn("README.md#L12", fields["body"][0])
        self.assertEqual(fields["body"], [handoff.body])
        self.assertNotIn("?title=", handoff.review(Snapshot()))

    def test_issue_templates_use_chooser_without_injecting_text(self):
        snapshot = Snapshot((".github/ISSUE_TEMPLATE/bug.yml",))
        handoff = prepare_handoff(API({"has_issues": True}), snapshot, SimpleNamespace(publish="issue"),
                                  SPEC, EVIDENCE, None, [])
        self.assertTrue(handoff.chrome_url().endswith("/issues/new/choose"))

    def test_disabled_issues_and_potential_secrets_are_rejected(self):
        args = SimpleNamespace(publish="issue")
        for api, spec in ((API({"has_issues": False}), SPEC),
                          (API({"has_issues": True}), SPEC | {"impact": "ghp_secretflow"})):
            with self.assertRaises(WorkbenchError):
                prepare_handoff(api, Snapshot(), args, spec, EVIDENCE, None, [])

    def test_pr_checks_published_base_head_and_changed_file_list(self):
        remote = {
            "base_commit": {"sha": BASE}, "status": "ahead", "total_commits": 1,
            "commits": [{"sha": HEAD}], "files": [{"filename": "README.md"}],
        }
        args = SimpleNamespace(publish="pr", pr_base="main", pr_head="contributor:fix/docs", pr_head_sha=HEAD)
        api = API(remote)
        handoff = prepare_handoff(api, Snapshot(), args, SPEC, EVIDENCE, {"number": 12}, [])
        self.assertIn("contributor:fix%2Fdocs?quick_pull=1", handoff.url)
        self.assertIn("Related issue: #12", handoff.body)
        self.assertEqual(handoff.head_sha, HEAD)
        for drift in ({"base_commit": {"sha": HEAD}}, {"files": [{"filename": "extra.py"}]}):
            with self.assertRaises(WorkbenchError):
                prepare_handoff(API(remote | drift), Snapshot(), args, SPEC, EVIDENCE, None, [])
