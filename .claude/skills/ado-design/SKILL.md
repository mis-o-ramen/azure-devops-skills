---
name: ado-design
description: アイデア・構想・要望を、Azure DevOps の受け入れ基準まで埋まった作業アイテムに落とし込む設計工程。設計相談、方針の検討と選択肢の比較、仕様の詰め、フィーチャーとユーザーストーリーへの分割、起票までを行う。ユーザーが「設計したい」「設計相談」「どう作るか決めたい」「仕様に落としたい」「作業アイテムにしたい」「起票したい」「ストーリーに分割したい」と言ったとき、または粗いアイデア・企画・要望を実装可能な形にしたいときに使う。Turn rough ideas into implementable Azure DevOps work items with acceptance criteria.
---

# 設計 — アイデアを作業アイテムに落とす

手順の骨格は兄弟スキル `../hotl-loop/references/stages/design.md` にあり、**必ず読んで
従う**(聞き取り → 既存調査 → 方針選択 → 本文承認 → 起票。質問・選択肢・設計判断・
受け入れ基準の上限もそこにある)。ループ全体の定義は `../hotl-loop/SKILL.md`、
Azure DevOps への対応づけは `../azure-devops/references/loop.md`。
ここに書くのは、この工程の ADO 固有の操作と差分だけ。

## この段の入口

入口条件と段の振り分けは `../azure-devops/references/loop.md` の表で判定する。
起点はチャットの依頼でも、粗く起票済みの作業アイテムでもよい。作業アイテムが起点なら
`wit get` と `wit comments` で読んでから始める。

## 能力層

Azure DevOps の操作(`wit …` / `pr …` / `build …`)はすべて兄弟スキル `azure-devops` の
`scripts/ado.py` を通す。コマンドの一覧・セットアップ・フィールドの調べ方は
`../azure-devops/SKILL.md`。兄弟配置(同じ skills ディレクトリ直下)が前提。

## ADO 固有の操作

- **既存調査** — 同じ課題を扱った作業アイテムを `wit query` で探す(WIQL は
  `../azure-devops/references/recipes.md`)。ネットワークが社内に閉じている場合、
  外部の検索や取得は使えない。到達できない情報源を前提にした計画を立てない
- **本文のフィールド** — 型ごとのフィールドは `wit describe-type` で確認する
  (`../azure-devops/SKILL.md` の「最初にフィールドを調べる」)。骨格の「背景」は説明
  フィールドに、「受け入れ条件」は受け入れ基準フィールドに、「設計判断」は説明の
  末尾に書く
- **本文は起票前に固める** — `html` 型フィールドは起票後に読んで書き戻す修正が
  できないため(`../azure-devops/SKILL.md`)、本文承認は起票前に得るのが安い。
  軽微な修正指示はそのまま反映して起票してよく、再提示は要らない
- **起票** — 分割した場合は親フィーチャーから先に作り、子は `--parent` でぶら下げる

  ```
  wit create --type "User Story" --title "…" --description @body.md \
    --field-multiline Microsoft.VSTS.Common.AcceptanceCriteria=@criteria.md
  wit create --type "User Story" --title "…" --parent <親id> …
  ```

- **報告** — 起点が既存の作業アイテムなら、そこに `wit comment` で起票した ID と URL を
  1 行ずつ報告する

やらないことは骨格と `../azure-devops/references/loop.md`(`System.State` 不変、
承認なしの起票禁止など)に従う。
