---
name: github-issue-driven-dev
description: "Use for GitHub-centered AI development workflows: define one Issue as the goal, generate a linked Beads epic and executable TODOs after requirements are ready, use issue-numbered branches, keep Japanese Issue and PR titles with 【repo名】 prefixes, write knowledge logs to Issues, manage PRs and GitHub Projects, and run quality gates."
metadata:
  short-description: GitHub中心のIssue駆動AI開発ワークフロー
---

# GitHub Issue-Driven Development

## Parent Skill

When this Skill is used for implementation or as part of autonomous or scheduled development loops, first read `~/.agents/skills/loop-engineering-core/SKILL.md` if it exists. If it is missing, continue with this Skill and report that the parent Skill was unavailable.

The parent owns shared loop rules (requirements gate, maker/checker separation, hard stops, Draft PR stop points). This Skill owns the GitHub Issue / branch / PR / Project workflow details.

## One Issue, One Goal Loop

Map the parent Issue Goal Loop onto GitHub. Treat one ready Issue as the durable container for one bounded goal loop and at most one Draft PR. Do not create a new Issue for each iteration.

Before implementation, ensure the Issue contains:

- loop goal, purpose, scope, and non-goals
- observable acceptance criteria
- linked tests or `test-board.yaml` cases and verification plan
- complete and blocked exit conditions
- hard stops, including attempt, cost, time, environment, and approval limits
- an iteration knowledge log

For each iteration, read the same Issue, select the smallest unmet acceptance criterion, run the needed workflow stage, perform a separate checker pass, and append evidence, failures, the current unmet condition, and the next action. Re-evaluate the whole Issue after every iteration.

Close the loop only by creating or updating its Draft PR after all criteria pass, or by leaving the Issue open with a blocked report that records the cause, attempts, required human decision, and exact resume point. Split a follow-up Issue only when discovered work changes the approved scope or delivers independent value.

## Issue to Beads

After the requirements gate passes, decompose the ready Issue into Beads. GitHub remains the source of truth for the goal, scope, acceptance criteria, decisions, and completion. Beads is the source of truth for fine-grained execution TODOs.

- Create exactly one Beads epic for the GitHub Issue.
- Set the epic `external_ref` to the Issue URL and store `github_repository`, `github_issue`, and `link_role=epic` in metadata.
- Create child tasks with `--parent <epic-id>`. Give every task a stable `plan_key` in metadata so rerunning the same plan updates rather than duplicates it.
- Express execution order with Beads dependencies, then select runnable work with `bd ready`.
- Write the epic ID and child task IDs into the managed `## Beads TODO` block in the GitHub Issue.
- Do not publish each Beads child as a separate GitHub Issue. Create another GitHub Issue only for independent or newly approved scope.

Use the bundled `scripts/issue_to_beads.py`. It accepts a reviewed plan JSON and is dry-run by default:

```json
{
  "epic": {"title": "Issueの実行計画", "priority": 2},
  "tasks": [
    {"key": "spec", "title": "仕様を確定する", "depends_on": []},
    {"key": "build", "title": "実装する", "depends_on": ["spec"]},
    {"key": "verify", "title": "検証する", "depends_on": ["build"]}
  ]
}
```

```bash
python3 scripts/issue_to_beads.py \
  --repo owner/repo --issue 123 --plan-file /path/to/plan.json
python3 scripts/issue_to_beads.py \
  --repo owner/repo --issue 123 --plan-file /path/to/plan.json \
  --apply --write-issue --init-if-missing
```

`--init-if-missing` initializes Beads in stealth mode without installing hooks or agent instructions. Inspect the local database through `bd list --all --json`, `bd show <id> --json`, or `bd ready --json`. A stealth database is local to that checkout unless a Beads/Dolt remote is configured.

If `bd` is unavailable, record that fact in the Issue and keep the implementation/test plan there. Do not pretend Beads IDs were created. If the user explicitly requires Beads, install or otherwise unblock `bd` before implementation.

Use this skill when a user asks for coding, product development, refactoring, bug fixes, app work, GitHub Issues / Projects / PR workflow setup, or reusable AI development process guidance, unless they explicitly ask for investigation only, a short answer only, or no code changes.

## Quick Command

This skill includes a helper CLI at `scripts/codex-gh-workflow`. Prefer a globally installed `codex-gh-workflow` if available; otherwise run the bundled script from this skill folder.

Common commands:

```bash
scripts/codex-gh-workflow status
scripts/codex-gh-workflow board-url
scripts/codex-gh-workflow draft-issue --title "【repo名】日本語タイトル" --body-file issue.md
scripts/codex-gh-workflow start --issue 123 --slug short-title
scripts/codex-gh-workflow install-hooks
scripts/codex-gh-workflow install-repo-instructions
scripts/codex-gh-workflow install-repo-templates
scripts/codex-gh-workflow install-repo-labels
scripts/codex-gh-workflow install-bin
python3 scripts/issue_to_beads.py --help
```

If the user wants the command on PATH, run:

```bash
scripts/codex-gh-workflow install-bin
```

## Workflow

1. Check context before editing:
   - `git status --short`
   - `git remote -v`
   - `git branch --show-current`
   - `scripts/codex-gh-workflow status` when available
2. Create or identify a GitHub Issue before implementation.
   - Title format: `【repo名】日本語タイトル`
   - Body language: Japanese
   - Include the One Issue, One Goal Loop fields above, implementation plan, test / CI plan, and knowledge log.
   - If GitHub write access is unavailable, create a local draft under `.codex/issue-drafts/` or `.codex/issue-knowledge/`.
3. If requirements are vague, do a short Goal Prepare:
   - restate the goal
   - identify users, constraints, non-goals, risks, and dependencies
   - define completion criteria and verification
   - ask at most three necessary questions
4. After requirements are ready, generate or update the Issue-linked Beads epic and child TODOs.
   - Derive the plan from the Issue's implementation and test plan.
   - Preview first, then apply and write the IDs back to the same Issue.
   - Use `bd ready --json` to choose the next unblocked TODO.
5. Work on an issue-numbered branch:

```bash
scripts/codex-gh-workflow start --issue 123 --slug short-title
```

6. Commit in meaningful units.
   - Include `Refs #123`, `Closes #123`, or `Fixes #123`.
   - Do not include unrelated user changes.
   - If a remote exists, push created commits.
7. Keep the Issue as the goal and knowledge record; update Beads task status as work advances.
   - Record decisions, touched files, constraints, commands, test results, CI failures, fixes, and follow-ups in the Issue knowledge log.
   - Local knowledge logs are only a fallback, not a replacement for Git history.
8. Run relevant quality gates before completion.
   - Prefer repo-native `test`, `lint`, `typecheck`, and `build`.
   - Report any gate that could not run and why.
9. Re-evaluate every acceptance criterion after the checker pass.
   - Continue the same Issue goal loop while safe, in scope, and incomplete.
   - Stop with a blocked report when a parent hard stop is reached.
10. Close completed Beads child TODOs and the epic, then create a Draft PR for substantial completed work.
   - PR title format: `【repo名】日本語タイトル`
   - PR body language: Japanese
   - Include `Closes #123`, summary, verification, and risk.
11. Add or reference the Issue / PR in the cross-repo GitHub Project when configured.
   - Show the board view URL after adding or referencing board work:

```text
https://github.com/users/nanameru/projects/3/views/3
```

## Naming Rules

User-visible task names must be Japanese and begin with `【repo名】`:

- GitHub Issue titles
- Pull Request titles
- GitHub Project draft titles
- board card titles

Technical names may remain English when appropriate:

- branch names
- labels
- commands
- package names
- code identifiers

## Repository Setup

Only install repository templates or instructions when the user wants repository-level setup.

```bash
scripts/codex-gh-workflow install-repo-instructions
scripts/codex-gh-workflow install-repo-templates
scripts/codex-gh-workflow install-repo-labels
scripts/codex-gh-workflow install-hooks
```

These commands add missing templates without overwriting existing files where possible.
