from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "skills/github-issue-driven-dev/scripts/issue_to_beads.py"


def load_module():
    spec = importlib.util.spec_from_file_location("issue_to_beads", SCRIPT_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class IssueToBeadsUnitTest(unittest.TestCase):
    def setUp(self) -> None:
        self.module = load_module()

    def test_rejects_duplicate_keys_and_dependency_cycles(self) -> None:
        with self.assertRaisesRegex(self.module.WorkflowError, "重複"):
            self.module.validate_plan(
                {
                    "tasks": [
                        {"key": "build", "title": "A"},
                        {"key": "build", "title": "B"},
                    ]
                }
            )

        with self.assertRaisesRegex(self.module.WorkflowError, "循環"):
            self.module.validate_plan(
                {
                    "tasks": [
                        {"key": "a", "title": "A", "depends_on": ["b"]},
                        {"key": "b", "title": "B", "depends_on": ["a"]},
                    ]
                }
            )

    def test_managed_block_replaces_only_managed_section(self) -> None:
        original = (
            "# Goal\n\nKeep this text.\n\n"
            f"{self.module.START_MARKER}\nold\n{self.module.END_MARKER}\n\n"
            "Keep this footer.\n"
        )
        updated = self.module.merge_managed_block(
            original,
            f"{self.module.START_MARKER}\nnew\n{self.module.END_MARKER}",
        )
        self.assertIn("Keep this text.", updated)
        self.assertIn("Keep this footer.", updated)
        self.assertIn("\nnew\n", updated)
        self.assertNotIn("\nold\n", updated)
        self.assertEqual(updated.count(self.module.START_MARKER), 1)

    def test_dry_run_does_not_initialize_beads(self) -> None:
        with tempfile.TemporaryDirectory() as repository_dir:
            repository = Path(repository_dir)
            issue_path = repository / "issue.json"
            plan_path = repository / "plan.json"
            issue_path.write_text(
                json.dumps(
                    {
                        "repository": "nanameru/github-issue-driven-dev-skill",
                        "number": 6,
                        "title": "Goal",
                        "body": "Body",
                        "url": "https://github.com/nanameru/github-issue-driven-dev-skill/issues/6",
                    }
                ),
                encoding="utf-8",
            )
            plan_path.write_text(
                json.dumps({"tasks": [{"key": "plan", "title": "Plan"}]}),
                encoding="utf-8",
            )
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT_PATH),
                    "--issue-json",
                    str(issue_path),
                    "--plan-file",
                    str(plan_path),
                    "--workdir",
                    str(repository),
                ],
                text=True,
                capture_output=True,
                check=True,
            )
            self.assertEqual(json.loads(result.stdout)["mode"], "dry-run")
            self.assertFalse((repository / ".beads").exists())


@unittest.skipUnless(shutil.which("bd") and shutil.which("git"), "bd and git are required")
class IssueToBeadsIntegrationTest(unittest.TestCase):
    def test_apply_is_idempotent_and_dependencies_control_ready_work(self) -> None:
        with tempfile.TemporaryDirectory() as repository_dir, tempfile.TemporaryDirectory() as input_dir:
            repository = Path(repository_dir)
            inputs = Path(input_dir)
            subprocess.run(["git", "init", "-q", str(repository)], check=True)

            issue_path = inputs / "issue.json"
            plan_path = inputs / "plan.json"
            issue_path.write_text(
                json.dumps(
                    {
                        "repository": "nanameru/github-issue-driven-dev-skill",
                        "number": 6,
                        "title": "IssueからTODOを作る",
                        "body": "Original body",
                        "url": "https://github.com/nanameru/github-issue-driven-dev-skill/issues/6",
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            plan_path.write_text(
                json.dumps(
                    {
                        "epic": {"acceptance": "子TODOが一意である"},
                        "tasks": [
                            {
                                "key": "spec",
                                "title": "仕様を定義する",
                                "acceptance": "入出力が決まる",
                            },
                            {
                                "key": "build",
                                "title": "実装する",
                                "depends_on": ["spec"],
                            },
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            command = [
                sys.executable,
                str(SCRIPT_PATH),
                "--issue-json",
                str(issue_path),
                "--plan-file",
                str(plan_path),
                "--workdir",
                str(repository),
                "--apply",
                "--init-if-missing",
            ]
            first = json.loads(
                subprocess.run(
                    command,
                    text=True,
                    capture_output=True,
                    check=True,
                ).stdout
            )
            second = json.loads(
                subprocess.run(
                    command,
                    text=True,
                    capture_output=True,
                    check=True,
                ).stdout
            )
            self.assertEqual(first["epic_id"], second["epic_id"])
            self.assertEqual(first["task_ids"], second["task_ids"])

            beads = json.loads(
                subprocess.run(
                    ["bd", "list", "--all", "--limit", "0", "--json"],
                    cwd=repository,
                    text=True,
                    capture_output=True,
                    check=True,
                ).stdout
            )
            self.assertEqual(len(beads), 3)
            epic = next(item for item in beads if item["issue_type"] == "epic")
            self.assertEqual(
                epic["external_ref"],
                "https://github.com/nanameru/github-issue-driven-dev-skill/issues/6",
            )
            self.assertEqual(epic["metadata"]["github_issue"], 6)

            tasks = {
                item["metadata"].get("plan_key"): item
                for item in beads
                if item["issue_type"] == "task"
            }
            self.assertEqual(tasks["spec"]["parent"], epic["id"])
            self.assertEqual(tasks["build"]["parent"], epic["id"])
            self.assertIn(
                tasks["spec"]["id"],
                {
                    dependency["depends_on_id"]
                    for dependency in tasks["build"]["dependencies"]
                    if dependency["type"] == "blocks"
                },
            )

            ready = json.loads(
                subprocess.run(
                    ["bd", "ready", "--json"],
                    cwd=repository,
                    text=True,
                    capture_output=True,
                    check=True,
                ).stdout
            )
            ready_ids = {item["id"] for item in ready}
            self.assertIn(tasks["spec"]["id"], ready_ids)
            self.assertNotIn(tasks["build"]["id"], ready_ids)


if __name__ == "__main__":
    unittest.main()

