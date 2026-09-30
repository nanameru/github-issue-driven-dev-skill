#!/usr/bin/env python3
"""Create one Beads epic and child TODOs for a GitHub Issue.

GitHub remains the goal and acceptance-criteria source of truth. Beads stores
the execution plan as one epic per Issue plus dependency-aware child tasks.
The command is dry-run by default and mutates state only with --apply.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


START_MARKER = "<!-- beads-todos:start -->"
END_MARKER = "<!-- beads-todos:end -->"
PLAN_KEY_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]*$")


class WorkflowError(RuntimeError):
    """Expected validation or external-command failure."""


def run_command(
    command: list[str],
    *,
    cwd: Path,
    input_text: str | None = None,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        command,
        cwd=cwd,
        input=input_text,
        text=True,
        capture_output=True,
        check=False,
    )
    if check and result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise WorkflowError(f"{' '.join(command)} failed: {detail}")
    return result


def read_json_file(path: str) -> Any:
    if path == "-":
        try:
            return json.load(sys.stdin)
        except json.JSONDecodeError as exc:
            raise WorkflowError(f"標準入力のJSONが不正です: {exc}") from exc

    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise WorkflowError(f"JSONファイルがありません: {path}") from exc
    except json.JSONDecodeError as exc:
        raise WorkflowError(f"JSONファイルが不正です ({path}): {exc}") from exc


def normalize_issue(raw: Any, repository: str | None) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise WorkflowError("Issue JSONはobjectで指定してください")

    repo = repository or raw.get("repository") or raw.get("repository_full_name")
    if not isinstance(repo, str) or "/" not in repo:
        raise WorkflowError("--repo または Issue JSONのrepositoryが必要です")

    try:
        number = int(raw["number"])
    except (KeyError, TypeError, ValueError) as exc:
        raise WorkflowError("Issue JSONのnumberは正の整数で指定してください") from exc
    if number <= 0:
        raise WorkflowError("Issue番号は正の整数で指定してください")

    title = raw.get("title")
    if not isinstance(title, str) or not title.strip():
        raise WorkflowError("Issue JSONのtitleが必要です")

    body = raw.get("body") or ""
    if not isinstance(body, str):
        raise WorkflowError("Issue JSONのbodyは文字列で指定してください")

    url = raw.get("url") or f"https://github.com/{repo}/issues/{number}"
    if not isinstance(url, str) or not url.startswith(("https://", "http://")):
        raise WorkflowError("Issue JSONのurlが不正です")

    return {
        "repository": repo,
        "number": number,
        "title": title.strip(),
        "body": body,
        "url": url,
    }


def fetch_issue(
    *,
    gh_bin: str,
    repository: str,
    issue_number: int,
    cwd: Path,
) -> dict[str, Any]:
    result = run_command(
        [
            gh_bin,
            "issue",
            "view",
            str(issue_number),
            "--repo",
            repository,
            "--json",
            "number,title,body,url",
        ],
        cwd=cwd,
    )
    try:
        raw = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise WorkflowError("gh issue viewのJSONを解析できません") from exc
    return normalize_issue(raw, repository)


def validate_plan(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise WorkflowError("計画JSONはobjectで指定してください")

    epic = raw.get("epic") or {}
    if not isinstance(epic, dict):
        raise WorkflowError("epicはobjectで指定してください")

    raw_tasks = raw.get("tasks")
    if not isinstance(raw_tasks, list) or not raw_tasks:
        raise WorkflowError("tasksには1件以上のTODOが必要です")

    tasks: list[dict[str, Any]] = []
    keys: set[str] = set()
    for index, raw_task in enumerate(raw_tasks, start=1):
        if not isinstance(raw_task, dict):
            raise WorkflowError(f"tasks[{index}]はobjectで指定してください")

        key = raw_task.get("key")
        if not isinstance(key, str) or not PLAN_KEY_PATTERN.fullmatch(key):
            raise WorkflowError(
                f"tasks[{index}].keyは英小文字・数字・_・-で指定してください"
            )
        if key in keys:
            raise WorkflowError(f"TODOキーが重複しています: {key}")
        keys.add(key)

        title = raw_task.get("title")
        if not isinstance(title, str) or not title.strip():
            raise WorkflowError(f"tasks[{index}].titleが必要です")

        dependencies = raw_task.get("depends_on") or []
        if not isinstance(dependencies, list) or not all(
            isinstance(item, str) for item in dependencies
        ):
            raise WorkflowError(f"tasks[{index}].depends_onは文字列配列で指定してください")

        priority = raw_task.get("priority", 2)
        if not isinstance(priority, int) or not 0 <= priority <= 4:
            raise WorkflowError(f"tasks[{index}].priorityは0〜4で指定してください")

        tasks.append(
            {
                "key": key,
                "title": title.strip(),
                "description": str(raw_task.get("description") or "").strip(),
                "acceptance": str(raw_task.get("acceptance") or "").strip(),
                "priority": priority,
                "depends_on": dependencies,
            }
        )

    for task in tasks:
        for dependency in task["depends_on"]:
            if dependency not in keys:
                raise WorkflowError(
                    f"{task['key']} が存在しないTODOへ依存しています: {dependency}"
                )
            if dependency == task["key"]:
                raise WorkflowError(f"{task['key']} は自分自身へ依存できません")

    detect_dependency_cycle(tasks)

    epic_priority = epic.get("priority", 2)
    if not isinstance(epic_priority, int) or not 0 <= epic_priority <= 4:
        raise WorkflowError("epic.priorityは0〜4で指定してください")

    return {
        "epic": {
            "title": str(epic.get("title") or "").strip(),
            "description": str(epic.get("description") or "").strip(),
            "acceptance": str(epic.get("acceptance") or "").strip(),
            "priority": epic_priority,
        },
        "tasks": tasks,
    }


def detect_dependency_cycle(tasks: list[dict[str, Any]]) -> None:
    dependencies = {task["key"]: task["depends_on"] for task in tasks}
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(key: str) -> None:
        if key in visiting:
            raise WorkflowError(f"TODO依存関係に循環があります: {key}")
        if key in visited:
            return
        visiting.add(key)
        for dependency in dependencies[key]:
            visit(dependency)
        visiting.remove(key)
        visited.add(key)

    for key in dependencies:
        visit(key)


def issue_metadata(issue: dict[str, Any], *, role: str, plan_key: str = "") -> dict[str, Any]:
    metadata: dict[str, Any] = {
        "github_repository": issue["repository"],
        "github_issue": issue["number"],
        "link_role": role,
    }
    if plan_key:
        metadata["plan_key"] = plan_key
    return metadata


def metadata_matches(
    item: dict[str, Any],
    issue: dict[str, Any],
    *,
    role: str,
    plan_key: str = "",
) -> bool:
    metadata = item.get("metadata") or {}
    return (
        metadata.get("github_repository") == issue["repository"]
        and metadata.get("github_issue") == issue["number"]
        and metadata.get("link_role") == role
        and (not plan_key or metadata.get("plan_key") == plan_key)
    )


def ensure_beads(
    *,
    bd_bin: str,
    cwd: Path,
    init_if_missing: bool,
) -> None:
    info = run_command([bd_bin, "info", "--json"], cwd=cwd, check=False)
    if info.returncode == 0:
        return
    if not init_if_missing:
        raise WorkflowError(
            "Beadsが未初期化です。安全確認後に "
            "`bd init --skip-agents --skip-hooks --non-interactive` を実行するか、"
            "--init-if-missingを指定してください"
        )
    run_command(
        [
            bd_bin,
            "init",
            "--stealth",
            "--skip-agents",
            "--skip-hooks",
            "--non-interactive",
        ],
        cwd=cwd,
    )


def list_beads(*, bd_bin: str, cwd: Path) -> list[dict[str, Any]]:
    result = run_command(
        [bd_bin, "list", "--all", "--limit", "0", "--json"],
        cwd=cwd,
    )
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise WorkflowError("bd listのJSONを解析できません") from exc
    if not isinstance(payload, list):
        raise WorkflowError("bd listのJSON形式が想定外です")
    return payload


def one_match(items: list[dict[str, Any]], description: str) -> dict[str, Any] | None:
    if len(items) > 1:
        ids = ", ".join(str(item.get("id")) for item in items)
        raise WorkflowError(f"{description}が重複しています: {ids}")
    return items[0] if items else None


def create_or_update_epic(
    *,
    bd_bin: str,
    cwd: Path,
    issue: dict[str, Any],
    epic_plan: dict[str, Any],
    items: list[dict[str, Any]],
) -> str:
    matches = [
        item
        for item in items
        if item.get("issue_type") == "epic"
        and metadata_matches(item, issue, role="epic")
    ]
    existing = one_match(matches, "このGitHub Issueに紐づくEpic")
    title = epic_plan["title"] or issue["title"]
    description = epic_plan["description"] or (
        f"GitHub Issue #{issue['number']} の実行TODOグループ。"
        f"ゴールと受入条件の正本: {issue['url']}"
    )
    metadata = json.dumps(
        issue_metadata(issue, role="epic"),
        ensure_ascii=False,
        separators=(",", ":"),
    )
    label = f"github-issue-{issue['number']}"

    if existing:
        command = [
            bd_bin,
            "update",
            existing["id"],
            "--title",
            title,
            "--description",
            description,
            "--priority",
            str(epic_plan["priority"]),
            "--external-ref",
            issue["url"],
            "--metadata",
            metadata,
            "--add-label",
            label,
        ]
        if epic_plan["acceptance"]:
            command.extend(["--acceptance", epic_plan["acceptance"]])
        run_command(command, cwd=cwd)
        return str(existing["id"])

    command = [
        bd_bin,
        "create",
        title,
        "--type",
        "epic",
        "--description",
        description,
        "--priority",
        str(epic_plan["priority"]),
        "--external-ref",
        issue["url"],
        "--metadata",
        metadata,
        "--labels",
        label,
        "--silent",
    ]
    if epic_plan["acceptance"]:
        command.extend(["--acceptance", epic_plan["acceptance"]])
    result = run_command(command, cwd=cwd)
    epic_id = result.stdout.strip().splitlines()[-1]
    if not epic_id:
        raise WorkflowError("bd createからEpic IDを取得できません")
    return epic_id


def create_or_update_task(
    *,
    bd_bin: str,
    cwd: Path,
    issue: dict[str, Any],
    epic_id: str,
    task_plan: dict[str, Any],
    items: list[dict[str, Any]],
) -> str:
    matches = [
        item
        for item in items
        if item.get("issue_type") == "task"
        and metadata_matches(
            item,
            issue,
            role="todo",
            plan_key=task_plan["key"],
        )
    ]
    existing = one_match(matches, f"TODOキー {task_plan['key']}")
    metadata = json.dumps(
        issue_metadata(issue, role="todo", plan_key=task_plan["key"]),
        ensure_ascii=False,
        separators=(",", ":"),
    )
    label = f"github-issue-{issue['number']}"

    if existing:
        command = [
            bd_bin,
            "update",
            existing["id"],
            "--title",
            task_plan["title"],
            "--description",
            task_plan["description"],
            "--priority",
            str(task_plan["priority"]),
            "--parent",
            epic_id,
            "--metadata",
            metadata,
            "--add-label",
            label,
        ]
        if task_plan["acceptance"]:
            command.extend(["--acceptance", task_plan["acceptance"]])
        run_command(command, cwd=cwd)
        return str(existing["id"])

    command = [
        bd_bin,
        "create",
        task_plan["title"],
        "--type",
        "task",
        "--description",
        task_plan["description"],
        "--priority",
        str(task_plan["priority"]),
        "--parent",
        epic_id,
        "--metadata",
        metadata,
        "--labels",
        label,
        "--silent",
    ]
    if task_plan["acceptance"]:
        command.extend(["--acceptance", task_plan["acceptance"]])
    result = run_command(command, cwd=cwd)
    task_id = result.stdout.strip().splitlines()[-1]
    if not task_id:
        raise WorkflowError(f"TODO {task_plan['key']} のIDを取得できません")
    return task_id


def add_missing_dependencies(
    *,
    bd_bin: str,
    cwd: Path,
    plan: dict[str, Any],
    task_ids: dict[str, str],
    items: list[dict[str, Any]],
) -> None:
    items_by_id = {str(item.get("id")): item for item in items}
    for task in plan["tasks"]:
        task_id = task_ids[task["key"]]
        current = items_by_id.get(task_id, {})
        existing = {
            str(dependency.get("depends_on_id"))
            for dependency in current.get("dependencies") or []
            if dependency.get("type") == "blocks"
        }
        for dependency_key in task["depends_on"]:
            dependency_id = task_ids[dependency_key]
            if dependency_id not in existing:
                run_command(
                    [bd_bin, "dep", "add", task_id, dependency_id],
                    cwd=cwd,
                )


def render_managed_block(
    *,
    issue: dict[str, Any],
    epic: dict[str, Any],
    tasks: list[dict[str, Any]],
    task_ids: dict[str, str],
) -> str:
    lines = [
        START_MARKER,
        "## Beads TODO",
        "",
        f"- Epic ID: `{epic['id']}`",
        f"- GitHub Issue: [#{issue['number']}]({issue['url']})",
        "- ゴールの正本: GitHub Issue",
        "- 実行TODOの正本: Beads",
        "",
        "| Beads ID | TODO | 状態 | 依存先 |",
        "|---|---|---|---|",
    ]
    for task in tasks:
        dependency_ids = [f"`{task_ids[key]}`" for key in task["depends_on"]]
        dependencies = ", ".join(dependency_ids) if dependency_ids else "—"
        title = task["title"].replace("|", "\\|")
        lines.append(
            f"| `{task['id']}` | {title} | `{task['status']}` | {dependencies} |"
        )
    lines.extend(
        [
            "",
            "更新方法: 同じ計画JSONでSkill同梱の `scripts/issue_to_beads.py --apply --write-issue` "
            "を再実行する。",
            END_MARKER,
        ]
    )
    return "\n".join(lines)


def merge_managed_block(body: str, block: str) -> str:
    pattern = re.compile(
        rf"{re.escape(START_MARKER)}.*?{re.escape(END_MARKER)}",
        re.DOTALL,
    )
    if pattern.search(body):
        return pattern.sub(block, body, count=1)
    stripped = body.rstrip()
    return f"{stripped}\n\n{block}\n" if stripped else f"{block}\n"


def apply_plan(
    *,
    bd_bin: str,
    cwd: Path,
    issue: dict[str, Any],
    plan: dict[str, Any],
    init_if_missing: bool,
) -> dict[str, Any]:
    ensure_beads(bd_bin=bd_bin, cwd=cwd, init_if_missing=init_if_missing)
    items = list_beads(bd_bin=bd_bin, cwd=cwd)
    epic_id = create_or_update_epic(
        bd_bin=bd_bin,
        cwd=cwd,
        issue=issue,
        epic_plan=plan["epic"],
        items=items,
    )

    items = list_beads(bd_bin=bd_bin, cwd=cwd)
    task_ids: dict[str, str] = {}
    for task in plan["tasks"]:
        task_ids[task["key"]] = create_or_update_task(
            bd_bin=bd_bin,
            cwd=cwd,
            issue=issue,
            epic_id=epic_id,
            task_plan=task,
            items=items,
        )
        items = list_beads(bd_bin=bd_bin, cwd=cwd)

    add_missing_dependencies(
        bd_bin=bd_bin,
        cwd=cwd,
        plan=plan,
        task_ids=task_ids,
        items=list_beads(bd_bin=bd_bin, cwd=cwd),
    )

    refreshed = list_beads(bd_bin=bd_bin, cwd=cwd)
    by_id = {str(item.get("id")): item for item in refreshed}
    epic = by_id[epic_id]
    tasks: list[dict[str, Any]] = []
    for task_plan in plan["tasks"]:
        item = dict(by_id[task_ids[task_plan["key"]]])
        item["key"] = task_plan["key"]
        item["depends_on"] = task_plan["depends_on"]
        tasks.append(item)

    return {
        "epic": epic,
        "tasks": tasks,
        "task_ids": task_ids,
    }


def write_issue_body(
    *,
    gh_bin: str,
    cwd: Path,
    issue: dict[str, Any],
    body: str,
) -> None:
    run_command(
        [
            gh_bin,
            "issue",
            "edit",
            str(issue["number"]),
            "--repo",
            issue["repository"],
            "--body-file",
            "-",
        ],
        cwd=cwd,
        input_text=body,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="GitHub Issueを1つのBeads Epicと子TODOへ変換します",
    )
    parser.add_argument("--repo", help="GitHub repository（owner/name）")
    parser.add_argument("--issue", type=int, help="GitHub Issue番号")
    parser.add_argument(
        "--issue-json",
        help="GitHub取得を使わないIssue JSON（テスト・オフライン用）",
    )
    parser.add_argument("--plan-file", required=True, help="TODO計画JSON。- は標準入力")
    parser.add_argument(
        "--workdir",
        default=".",
        help="Beadsを操作するGitリポジトリ（既定: current directory）",
    )
    parser.add_argument("--bd-bin", default="bd", help="bd executable")
    parser.add_argument("--gh-bin", default="gh", help="gh executable")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Beadsへ書き込む（未指定時はdry-run）",
    )
    parser.add_argument(
        "--write-issue",
        action="store_true",
        help="管理ブロックをGitHub Issue本文へ書き戻す（--apply必須）",
    )
    parser.add_argument(
        "--init-if-missing",
        action="store_true",
        help="Beads未初期化時にstealth modeで安全に初期化する",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    cwd = Path(args.workdir).resolve()
    if not cwd.is_dir():
        raise WorkflowError(f"workdirがありません: {cwd}")
    if args.write_issue and not args.apply:
        raise WorkflowError("--write-issueには--applyが必要です")
    if args.write_issue and args.issue_json:
        raise WorkflowError(
            "--issue-json使用時はGitHub本文を書き戻せません。"
            "--repoと--issueで取得してください"
        )

    if args.issue_json:
        issue = normalize_issue(read_json_file(args.issue_json), args.repo)
    else:
        if not args.repo or not args.issue:
            raise WorkflowError("--issue-jsonを使わない場合は--repoと--issueが必要です")
        gh_bin = shutil.which(args.gh_bin) or args.gh_bin
        issue = fetch_issue(
            gh_bin=gh_bin,
            repository=args.repo,
            issue_number=args.issue,
            cwd=cwd,
        )

    plan = validate_plan(read_json_file(args.plan_file))
    preview = {
        "mode": "apply" if args.apply else "dry-run",
        "issue": {
            "repository": issue["repository"],
            "number": issue["number"],
            "title": issue["title"],
            "url": issue["url"],
        },
        "epic": {
            **plan["epic"],
            "title": plan["epic"]["title"] or issue["title"],
            "external_ref": issue["url"],
        },
        "tasks": plan["tasks"],
    }
    if not args.apply:
        print(json.dumps(preview, ensure_ascii=False, indent=2))
        return 0

    bd_bin = shutil.which(args.bd_bin) or args.bd_bin
    applied = apply_plan(
        bd_bin=bd_bin,
        cwd=cwd,
        issue=issue,
        plan=plan,
        init_if_missing=args.init_if_missing,
    )
    block = render_managed_block(
        issue=issue,
        epic=applied["epic"],
        tasks=applied["tasks"],
        task_ids=applied["task_ids"],
    )
    issue_body = merge_managed_block(issue["body"], block)

    if args.write_issue:
        gh_bin = shutil.which(args.gh_bin) or args.gh_bin
        write_issue_body(
            gh_bin=gh_bin,
            cwd=cwd,
            issue=issue,
            body=issue_body,
        )

    result = {
        **preview,
        "epic_id": applied["epic"]["id"],
        "task_ids": applied["task_ids"],
        "issue_body_updated": bool(args.write_issue),
        "managed_block": block,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except WorkflowError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(2)

