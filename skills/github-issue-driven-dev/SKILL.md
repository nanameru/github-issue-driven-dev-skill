---
name: github-issue-driven-dev
description: "Use for GitHub-centered AI development workflows: create or reuse Issues before coding, use issue-numbered branches, keep Japanese Issue and PR titles with 【repo名】 prefixes, write knowledge logs to Issues, manage PRs and GitHub Projects, and run local quality gates before completion."
metadata:
  short-description: GitHub中心のIssue駆動AI開発ワークフロー
---

# GitHub Issue-Driven Development

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
   - Include purpose, scope, acceptance criteria, implementation plan, test / CI plan, and knowledge log.
   - If GitHub write access is unavailable, create a local draft under `.codex/issue-drafts/` or `.codex/issue-knowledge/`.
3. If requirements are vague, do a short Goal Prepare:
   - restate the goal
   - identify users, constraints, non-goals, risks, and dependencies
   - define completion criteria and verification
   - ask at most three necessary questions
4. Work on an issue-numbered branch:

```bash
scripts/codex-gh-workflow start --issue 123 --slug short-title
```

5. Commit in meaningful units.
   - Include `Refs #123`, `Closes #123`, or `Fixes #123`.
   - Do not include unrelated user changes.
   - If a remote exists, push created commits.
6. Keep the Issue as the work record.
   - Record decisions, touched files, constraints, commands, test results, CI failures, fixes, and follow-ups in the Issue knowledge log.
   - Local knowledge logs are only a fallback, not a replacement for Git history.
7. Run relevant quality gates before completion.
   - Prefer repo-native `test`, `lint`, `typecheck`, and `build`.
   - Report any gate that could not run and why.
8. Create a Draft PR for substantial work.
   - PR title format: `【repo名】日本語タイトル`
   - PR body language: Japanese
   - Include `Closes #123`, summary, verification, and risk.
9. Add or reference the Issue / PR in the cross-repo GitHub Project when configured.
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
