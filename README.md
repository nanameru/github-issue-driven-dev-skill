# GitHub Issue-Driven Dev Skill

GitHub Issueを中心に、AI開発作業を `Issue -> branch -> commit -> PR -> CI -> review` の流れで進めるためのAgent Skillです。

## Install

```bash
npx skills add nanameru/github-issue-driven-dev-skill -g -y
```

特定のSkillだけを指定する場合:

```bash
npx skills add nanameru/github-issue-driven-dev-skill --skill github-issue-driven-dev -g -y
```

## Included Command

Skill内に補助CLIを同梱しています。

```bash
scripts/codex-gh-workflow status
scripts/codex-gh-workflow draft-issue --title "【repo名】日本語タイトル" --body-file issue.md
scripts/codex-gh-workflow start --issue 123 --slug short-title
scripts/codex-gh-workflow install-bin
```

`install-bin` を実行すると `codex-gh-workflow` を `~/.local/bin` にシンボリックリンクします。

## Requirements

- Git
- GitHub CLI (`gh`) for GitHub writes
- `npx skills` for installation

GitHubへ書き込めない場合、Skillは `.codex/issue-drafts/` や `.codex/issue-knowledge/` をフォールバックとして使います。
