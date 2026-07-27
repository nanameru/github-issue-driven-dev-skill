# Repository GitHub Issue-Driven Development

このリポジトリのコーディング作業では、GitHubを作業記録の中心にする。

```text
要件 -> GitHub Issue -> Beads Epic/TODO -> ブランチ -> コミット -> Pull Request -> CI -> レビュー -> マージ -> リリース
```

Issueタイトル、PRタイトル、GitHub Project項目、Draftタスク、ボードカードなど、ユーザーに見えるタスク名は必ず日本語にする。さらに、横断ボードでリポジトリを識別できるよう、タイトル先頭に `【repo名】` を付ける。技術的なブランチ名、ラベル、コマンド、コード識別子は必要に応じて英語のままでよい。

Issue本文、PR本文、Project Draft本文、ナレッジログも日本語で書く。技術用語、ファイルパス、コマンド、API名は英語のままでよい。ナレッジログは補助記録であり、ファイル変更の履歴は必ずGitコミットで残す。remoteがある場合はコミットをpushする。

## 必須フロー

1. 編集前に `git status --short`、`git remote -v`、現在のブランチを確認する。
2. 実装前にGitHub Issueを作成または特定する。GitHubへ書けない場合は `.codex/issue-drafts/` にドラフトを残す。Issueタイトルは `【repo名】日本語タイトル` にする。
   - 1 Issueを1つのゴールループとして扱い、最大1つのDraft PRへ対応させる。
   - Issueにループゴール、scope、対象外、受入条件、検証方法、終了条件、強制停止条件、周回ログを持たせる。
3. 作業が曖昧な場合は、目的、対象範囲、対象外、完了条件、リスク、検証方法を先に整理する。
4. 要件確定後、1 Issueにつき1 Beads Epicを作り、実装計画とテスト計画を子TODOへ分解する。
   - Epicの`external_ref`とmetadataをGitHub Issueへ紐づけ、子TODOは`--parent`でグループ化する。
   - 各TODOへ安定した`plan_key`を持たせ、同じ計画の再適用で重複させない。
   - Issue本文の`## Beads TODO`管理ブロックへEpic IDとTODO IDを書き戻す。
   - GitHub Issueはゴールの正本、Beadsは実行TODOの正本とし、子TODOを個別のGitHub Issueへ変換しない。
5. `bd ready --json`から未ブロックのTODOを選び、ブランチ名は `issue-123-short-slug` のようにする。
6. コミットは小さく行い、`Refs #123`、`Closes #123`、`Fixes #123` のいずれかを含める。
7. 判断、発見、実行コマンド、CI結果、フォローアップはIssueのナレッジログへ残し、実行状態はBeadsへ反映する。GitHubへ書けない場合は `.codex/issue-knowledge/` に残す。
8. makerとは別のchecker観点で検証し、Issueの全受入条件を再判定する。未達成なら同じIssue内で次の周回を行う。
9. 全条件を満たしたらBeads TODOとEpicを完了し、PRを作成して関連Issueと検証結果を書く。PRタイトルは `【repo名】日本語タイトル` にする。強制停止条件へ達した場合は、Issueを開いたままblocked reportと再開点を残す。
10. remoteがある場合は、作成したコミットをpushする。PRがある場合はPRブランチへpushする。
11. final前に関連する test / lint / build を実行する。
12. 可能ならIssueとPRを横断GitHub Projectへ追加する。
13. タスクを追加または参照したら、必ずボードViewリンクを表示する: https://github.com/users/nanameru/projects/3/views/3

無関係なユーザー変更はコミットしない。テストやCIの失敗を隠さない。
