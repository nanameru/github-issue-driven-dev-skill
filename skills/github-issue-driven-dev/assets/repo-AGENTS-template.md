# Repository GitHub Issue-Driven Development

このリポジトリのコーディング作業では、GitHubを作業記録の中心にする。

```text
要件 -> GitHub Issue -> ブランチ -> コミット -> Pull Request -> CI -> レビュー -> マージ -> リリース
```

Issueタイトル、PRタイトル、GitHub Project項目、Draftタスク、ボードカードなど、ユーザーに見えるタスク名は必ず日本語にする。さらに、横断ボードでリポジトリを識別できるよう、タイトル先頭に `【repo名】` を付ける。技術的なブランチ名、ラベル、コマンド、コード識別子は必要に応じて英語のままでよい。

Issue本文、PR本文、Project Draft本文、ナレッジログも日本語で書く。技術用語、ファイルパス、コマンド、API名は英語のままでよい。ナレッジログは補助記録であり、ファイル変更の履歴は必ずGitコミットで残す。remoteがある場合はコミットをpushする。

## Checkerの検証記録

Makerとは独立したChecker（Devin）が検証し、Maker自身が自分の変更を合格にしてはならない。検証結果の正本はGitHub Issueコメントに残し、PRには要約コメントを1件だけ置く。更新時は新しいコメントを増やさず、そのコメントを編集する。判定は `合格`、`不合格`、`未検証あり` のいずれかとし、マージ／デプロイは人間が判断する。

## GitHub Actionsが実行できない場合

予算制限などでGitHub Actionsが動かない場合、DevinがVM上で同じ手順を実行し、記録に `「代替実行」` と明記する。実行したcommit SHA、コマンド、件数、時刻を記録する。代替実行はActionsの成功の代わりにはならないため、マージ前にActionsを再実行して成功を確認する。

認証状態マトリクスとセキュリティゲートの詳細は `loop-engineering-dev` スキルを参照し、ここでは重複して定義しない。

## 必須フロー

1. 編集前に `git status --short`、`git remote -v`、現在のブランチを確認する。
2. 実装前にGitHub Issueを作成または特定する。GitHubへ書けない場合は `.codex/issue-drafts/` にドラフトを残す。Issueタイトルは `【repo名】日本語タイトル` にする。
3. 作業が曖昧な場合は、目的、対象範囲、対象外、完了条件、リスク、検証方法を先に整理する。
4. ブランチ名は `issue-123-short-slug` のようにする。
5. コミットは小さく行い、`Refs #123`、`Closes #123`、`Fixes #123` のいずれかを含める。
6. 判断、発見、実行コマンド、CI結果、フォローアップはIssueのナレッジログへ残す。GitHubへ書けない場合は `.codex/issue-knowledge/` に残す。
7. PRを作成し、関連Issueと検証結果を書く。PRタイトルは `【repo名】日本語タイトル` にする。
8. remoteがある場合は、作成したコミットをpushする。PRがある場合はPRブランチへpushする。
9. final前に関連する test / lint / build を実行する。
10. 可能ならIssueとPRを横断GitHub Projectへ追加する。
11. タスクを追加または参照したら、必ずボードViewリンクを表示する: https://github.com/users/nanameru/projects/3/views/3

無関係なユーザー変更はコミットしない。テストやCIの失敗を隠さない。
