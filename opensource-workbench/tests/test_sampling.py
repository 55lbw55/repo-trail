import unittest
from types import SimpleNamespace

from workbench.contribution import policy
from workbench.sampling import command_finding, cobra_commands, config_finding, config_tags, markdown_parts, scan


class Snapshot:
    repo = "org/tool"
    sha = "a" * 40
    commit_link = "https://example.test/commit"
    incomplete = False

    def __init__(self, contents):
        self.contents = contents
        self.files = {path: {"size": len(text.encode())} for path, text in contents.items()}
        self.paths = set(self.files)
        self.reads = []

    def text(self, path):
        self.reads.append(path)
        return self.contents[path]

    def link(self, path, line=None):
        return f"https://example.test/{path}" + (f"#L{line}" if line else "")

    def policy_paths(self):
        return ["AGENTS.md", "docs/AGENTS.md", "other/AGENTS.md"]


def options(**overrides):
    defaults = dict(scope="docs", scan_rounds=2, scan_max_files=25, reference=None, local_repo=None)
    return SimpleNamespace(**(defaults | overrides))


class SamplingTests(unittest.TestCase):
    def test_large_project_reads_two_disjoint_five_percent_batches(self):
        contents = {f"docs/topic-{i}.md": "# Topic\n" for i in range(100)}
        contents.update({f"src/module_{i}.go": "package example" for i in range(1000)})
        snapshot = Snapshot(contents)
        report = "\n".join(scan(snapshot, options(), ["topic"]))
        self.assertIn("大型", report)
        self.assertIn("第 2 轮", report)
        self.assertIn("10/100", report)
        self.assertEqual(len(snapshot.reads), len(set(snapshot.reads)))

    def test_finding_stops_first_batch_early_and_ignores_fenced_links(self):
        contents = {
            "docs/priority.md": "```md\n[example](missing/target.md)\n```\n[real](old/target.md)\n",
            "docs/target.md": "# Target\n",
        }
        snapshot = Snapshot(contents)
        report = "\n".join(scan(snapshot, options(), ["priority"]))
        self.assertIn("old/target.md", report)
        self.assertNotIn("missing/target.md", report)
        self.assertEqual(snapshot.reads, ["docs/priority.md"])

    def test_budget_rounds_and_file_cap_both_apply(self):
        snapshot = Snapshot({f"docs/one-{i}.md": "# File\n" for i in range(100)})
        report = "\n".join(scan(snapshot, options(scan_max_files=7), ["one"]))
        self.assertIn("7/100", report)
        self.assertEqual(len(snapshot.reads), 7)

    def test_duplicate_directory_link_can_locate_source_file(self):
        contents = {
            "docs/guide.md": "[driver](../packages/core/packages/core/src/types.ts#L38)",
            "packages/core/src/types.ts": "export interface Driver {}",
            "packages/extra/src/types.ts": "export interface Extra {}",
        }
        report = "\n".join(scan(Snapshot(contents), options(), ["guide"]))
        self.assertIn("../packages/core/src/types.ts#L38", report)
        contents["docs/guide.md"] = "[driver](../old/types.ts)"
        report = "\n".join(scan(Snapshot(contents), options(), ["guide"]))
        self.assertNotIn("单个待核对线索", report)

    def test_go_squash_follows_same_repo_type_and_uses_its_line(self):
        snapshot = Snapshot({
            "receiver/config.go": 'package receiver\nimport alias "github.com/org/tool/internal/shared"\n'
                'type Config struct {\n  alias.Config `mapstructure:",squash"`\n}\n',
            "internal/shared/config.go": 'package shared\ntype Config struct {\n'
                '  Username string `mapstructure:"username"`\n  Driver string `mapstructure:"driver"`\n}\n'
                'type Other struct {\n  User string `mapstructure:"user"`\n}\n',
        })
        path = "receiver/config.go"
        tags = config_tags(snapshot, path, snapshot.text(path))
        _, examples = markdown_parts("```yaml\n  driver: postgres\n  user: sample\n```\n")
        result = config_finding("README.md", examples, tags)
        self.assertEqual((result.before, result.after), ("user:", "username:"))
        self.assertEqual((result.reference, result.reference_line), ("internal/shared/config.go", 3))

    def test_cobra_count_ignores_flag_value_and_valid_examples(self):
        commands = cobra_commands('createCmd := &cobra.Command{\n'
            '  Use: "create MODEL",\n  Args: cobra.ExactArgs(1),\n}\n'
            'createCmd.Flags().StringP("file", "f", "", "file")\n')
        _, examples = markdown_parts("```sh\ntool create sample -f ModelFile\ntool create --unknown\n"
                                    "tool create -f ModelFile\n```\n")
        result = command_finding("README.md", examples, "cmd.go", "tool", commands)
        self.assertEqual(result.line, 4)
        self.assertEqual(result.reference_line, 2)

    def test_policy_reads_root_and_scope_without_unrelated_component(self):
        snapshot = Snapshot({"AGENTS.md": "Instructions", "docs/AGENTS.md": "Do not write the PR description yourself.",
                             "other/AGENTS.md": "Other component."})
        _, human_body = policy(snapshot, ["docs/example.md"])
        self.assertTrue(human_body)
        self.assertEqual(snapshot.reads, ["AGENTS.md", "docs/AGENTS.md"])

    def test_stale_setup_command_needs_packaging_manifest_and_missing_script(self):
        contents = {
            "docs/install.md": "```console\n$ python setup.py install\n```\n",
            "pyproject.toml": '[build-system]\nrequires = ["setuptools"]\n[project]\nname = "tool"\n',
        }
        result = scan(Snapshot(contents), options(), ["install"])
        self.assertTrue(any("python -m pip install ." in line for line in result))
        result = scan(Snapshot(contents | {"setup.py": "# local installer"}), options(), ["install"])
        self.assertFalse(any("python -m pip install ." in line for line in result))

    def test_policy_recognizes_human_issue_body(self):
        snapshot = Snapshot({"AGENTS.md": "If you are opening an issue, we expect you to describe the problem in your own words."})
        _, human_body = policy(snapshot, [])
        self.assertTrue(human_body)


if __name__ == "__main__":
    unittest.main()
