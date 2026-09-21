---
name: ado-fix
description: Azure DevOps のプルリクエストに付いたレビュー指摘に対応し、同じブランチに修正を push して報告する修正工程。ユーザーが「指摘に対応して」「レビューコメントを直して」「指摘を捌いて」「レビューの修正をして」「PR の指摘対応」と言ったときに使う。指摘の分類（対応・見送り・判断保留）、優先度順の修正、テスト、push、対応報告までを行う。Address review feedback on an Azure DevOps pull request.
---

# 修正 — レビュー指摘に対応する

手順の骨格は兄弟スキル `../hotl-loop/references/stages/fix.md` にあり、**必ず読んで
従う**(指摘の分類 3 種と人間のコメント最優先、P0 → P1 → P2 の順序、誤動作指摘への
落ちるテスト先行、報告の表形式と上限、判断保留での停止)。ループ全体の定義は
`../hotl-loop/SKILL.md`、ADO への対応づけは `../azure-devops/references/loop.md`。
ここに書くのは、この工程の ADO 固有の操作と差分だけ。

## この段の入口

入口条件と段の振り分けは `../azure-devops/references/loop.md` の表で判定する
(直す側なら修正、見る側なら `ado-review`)。

## 能力層

Azure DevOps の操作はすべて兄弟スキル `azure-devops` の `scripts/ado.py` を通す
(`../azure-devops/SKILL.md`)。checkout・diff・commit・push は `git` CLI を使う。

## ADO 固有の操作

- **対象の特定** (骨格の手順 1) — `pr get <id> --repo <repo>` で
  `sourceRefName` / `targetRefName` を控え、ソースブランチを最新にして checkout する:

  ```
  git fetch origin
  git checkout <ソース> && git pull
  ```

- **指摘を読む** (手順 2) — `pr threads <id> --repo <repo> --unresolved-only`。
  対応方針に迷ったら `--unresolved-only` を外して全体を読む。解決済みのスレッドに
  人間の判断が残っていることがある
- **差分の把握** (手順 3) — `git diff origin/<ターゲット>...origin/<ソース>`
- **push** (手順 7) — `git push origin HEAD`(同じブランチへ。新ブランチ・force push・
  ターゲット直 push はしない)
- **報告** (手順 8) — `pr comment <id> --repo <repo> --text @report.md`。
  PR コメントは Markdown が効くので骨格の表形式をそのまま使う
  (`../azure-devops/references/writing.md`)

やらないことは骨格と `../azure-devops/references/loop.md` に従う。
