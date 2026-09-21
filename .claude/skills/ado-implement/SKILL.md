---
name: ado-implement
description: Azure DevOps の作業アイテム（ユーザーストーリー、フィーチャー、バグ、タスク、PBI）を実装し、プルリクエストを作るまでの実装工程。ユーザーが「実装したい」「実装に着手」「着手して」「この作業アイテムをやって」「2251 を実装して」のように言ったときに使う。数字だけの名前のファイル（2251.md など）や裸の数字は作業アイテム ID を指す設計メモであることが多く、その実装依頼もこの工程。受け入れ基準の確認、基準ごとのテストの割り振り、最小の実装、プルリクエスト作成、作業アイテムへの報告までを行う。Implement an Azure DevOps work item through to a pull request.
---

# 実装 — 作業アイテムを実装する

手順の骨格は兄弟スキル `../hotl-loop/references/stages/implement.md` にあり、**必ず
読んで従う**(条件を読む → 不足なら止まる → ブランチ → 全基準にテストを割り振り
落ちるテストを書く → 最小実装 → テストを通す → 承認を得て PR → 報告。PR 本文の
上限と「該当なし」の使い分けもそこと PR テンプレートにある)。ループ全体の定義は
`../hotl-loop/SKILL.md`、ADO への対応づけは `../azure-devops/references/loop.md`。
ここに書くのは、この工程の ADO 固有の操作と差分だけ。

## この段の入口

入口条件と段の振り分けは `../azure-devops/references/loop.md` の表で判定する。
依頼の中の数字だけのファイル名(`2251.md` など)や裸の数字は作業アイテム ID である
ことがある。`wit get` で引き当ててから始める。

## 能力層

Azure DevOps の操作はすべて兄弟スキル `azure-devops` の `scripts/ado.py` を通す
(`../azure-devops/SKILL.md`)。Git 操作(clone / diff / branch / commit / push)は
`git` CLI を使う。

## ADO 固有の操作

- **条件を読む** (骨格の手順 1) —

  ```
  wit get <id> --relations
  wit comments <id>
  ```

  受け入れ基準のフィールドは型ごとに違う。参照名を推測せず `wit describe-type` で
  確認する。ユーザーストーリーなら `Microsoft.VSTS.Common.AcceptanceCriteria`、
  バグなら `Microsoft.VSTS.TCM.ReproSteps` に条件が入っていることが多い。
  `relations` の親(フィーチャーなど)を辿って読む — 「なぜ」は親にある

- **不足なら止まる** (手順 2) — 不足している条件を 1 件 1 行で挙げて `wit comment` で
  投げ、そこで止める
- **ブランチ** (手順 3) — リポジトリの命名規則に従う。なければ `ai/wi-<id>`
- **本文の見出し** — リポジトリの PR テンプレートに合わせる
  (`.azuredevops/pull_request_template.md` / `.github/pull_request_template.md`)
- **承認を得て PR を作る** (手順 7) — `pr create` は既定でドラフトを作るので、
  `--publish` を付けるのは本文の承認を得たときだけ。承認を得られない非対話の実行では
  既定のまま(ドラフト)作り、公開の判断を人間に残す

  ```
  pr create --repo <repo> --source ai/wi-<id> --target <ターゲット> \
    --title "…" --description @body.md --work-item <id> --publish
  ```

  `--work-item` で作業アイテムに紐づける。紐づいていればレビュー側が `pr workitems`
  で受け入れ基準を読める。省くとレビューは差分しか見られない

- **報告** (手順 8) — `wit comment <id> --text "…"`。プルリクエストの URL と 1 行の
  サマリだけ(`wit comment` はプレーンテキスト —
  `../azure-devops/references/writing.md`)

やらないことは骨格と `../azure-devops/references/loop.md`(`System.State` 不変、
完了・破棄・投票の禁止、ターゲットへの直接 push 禁止など)に従う。
