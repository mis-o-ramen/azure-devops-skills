---
name: ado-review
description: Azure DevOps のプルリクエストをレビューし、優先度付きの指摘を投稿するレビュー工程。ユーザーが「レビューして」「PR を見て」「差分を確認して」「コードレビューして」「この PR どう思う」と言ったときに使う。紐づく作業アイテムの受け入れ基準との突き合わせ、ローカル clone からの差分取得、P0/P1/P2 の優先度判定、インライン・トップレベルの指摘投稿までを行う。Review an Azure DevOps pull request and post prioritized findings.
---

# レビュー — プルリクエストをレビューする

手順の骨格は兄弟スキル `../hotl-loop/references/stages/review.md` にあり、**必ず読んで
従う**(P0/P1/P2 の定義と機械的判定、指摘のブロック書式と上限、受け入れ基準・検証表
との突き合わせ、参照元 0 件ルール)。ループ全体の定義は `../hotl-loop/SKILL.md`、
ADO への対応づけは `../azure-devops/references/loop.md`。
ここに書くのは、この工程の ADO 固有の操作と差分だけ。

## この段の入口

入口条件と段の振り分けは `../azure-devops/references/loop.md` の表で判定する
(見る側ならレビュー、直す側なら `ado-fix`)。

## 能力層

Azure DevOps の操作はすべて兄弟スキル `azure-devops` の `scripts/ado.py` を通す
(`../azure-devops/SKILL.md`、WIQL やフィールドは `../azure-devops/references/recipes.md`)。
差分の取得はローカル clone に対する `git` CLI で行う(下記)。

## ADO 固有の操作

- **対象の特定** (骨格の手順 1) — `pr get <id> --repo <repo>`。
  `sourceRefName` / `targetRefName`(`refs/heads/` を外したもの)と
  `lastMergeSourceCommit` を控える
- **差分の取得** — 差分は REST では取得しない。Azure DevOps Server の REST が返すのは
  変更されたファイルの一覧までで、行単位のパッチは返らない。対象リポジトリの
  ローカル clone で取る(clone していない場合、この手順は成立しない):

  ```
  git fetch origin
  git diff origin/<ターゲット>...origin/<ソース>
  ```

- **満たすべき条件** (手順 2) — `pr workitems <id> --repo <repo>` で紐づく作業アイテムが
  フィールドごと返る。受け入れ基準(`Microsoft.VSTS.Common.AcceptanceCriteria`)と
  実装を突き合わせる
- **既出の指摘** (手順 3) — `pr threads <id> --repo <repo> --unresolved-only`
- **投稿** (手順 5) —

  ```
  pr comment <id> --repo <repo> --file <パス> --line <N> --text "…"   # インライン
  pr comment <id> --repo <repo> --text @review.md                      # トップレベル
  ```

  投稿の直前に、控えた `lastMergeSourceCommit` が `git rev-parse origin/<ソース>` と
  一致するか確認する。一致しなければレビュー中に新しい push が入っており、
  行番号がずれている。手順 1 からやり直す

やらないこと(完了・破棄・投票、スレッドの解決済み化、修正の代行)は骨格と
`../azure-devops/references/loop.md` に従う。
