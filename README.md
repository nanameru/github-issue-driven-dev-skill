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

## 30アプリの継続運用

複数アプリを継続運用する場合も、アプリごとに監視・デプロイ・秘密情報管理を個別実装せず、共通基盤を1つ用意します。日常開発はCodexを中心にし、隔離VM、長時間テスト、並列の独立検証など必要な作業だけをDevinへ渡します。

監視は運用負荷に応じて3段階に分けます。

| 段階 | 目安 | 標準装備 |
| --- | ---: | --- |
| A: 本番 | 3〜5アプリ | 外形監視、Sentry、バックアップ復元試験、Devin Oncall、Security Scan |
| B: β | 8〜10アプリ | 外形監視、Sentry、Slack通知、Security Scan。Oncallは使わない |
| C: 実験 | 15〜20アプリ | 最小限のログ・エラー監視と手動確認。Oncallは使わない |

Devin OncallはA段階だけに限定します。Security ScanとOncallの調査結果は読み取り専用で扱い、修正が必要なら別Issue・別セッションでDraft PRを作ります。自動マージ、本番デプロイ、権限変更、削除、課金追加は行いません。

通知はSlackの `#ops-alerts`（障害・稼働）と `#security-weekly`（セキュリティ）へ集約します。LINEはCritical/HighだけをCloudflare Worker等の安全な中継経由で送り、Devinから直接送信させません。チャネルIDは推測せず、接続後にSlack APIから取得した実IDを使います。

運用負荷は、週次30〜60分のトリアージと、月次1〜2時間の棚卸しを基本にします。詳細な段階分け、導入順序、必要な共通装備、承認境界は [`skills/github-issue-driven-dev/references/app-operations.md`](skills/github-issue-driven-dev/references/app-operations.md) を参照してください。
