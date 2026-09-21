# 開発ループ — Azure DevOps での対応

ループの正典は兄弟スキル `../../hotl-loop/SKILL.md`(段の定義・入口条件・承認点・
越えない線・今どの段かの判定)。**必ずそちらを読む。** hotl-loop は別リポジトリ
hotl-core のスキルで、導入手順に従って同じ skills ディレクトリに並べて配置する。
この文書に書くのは、その定義を Azure DevOps に対応づける差分だけ。
手順を足す・変えるときは、先に正典の表を更新する。

## 用語の対応

| コアの用語 | Azure DevOps では |
| --- | --- |
| チケット | 作業アイテム(ユーザーストーリー、フィーチャー、バグ、タスク、PBI) |
| 受け入れ条件 | 受け入れ基準。フィールドは型ごとに違う(`wit describe-type` で確認。ユーザーストーリーは `Microsoft.VSTS.Common.AcceptanceCriteria`、バグは `Microsoft.VSTS.TCM.ReproSteps` が多い) |
| プルリクエスト | Pull Request(`pr …` で操作。作成は既定でドラフト) |
| 着手承認 | 対話での依頼と、起票・作成前の本文承認 |
| 停止 | 対話で質問し、回答を待つ |

## 段と手順の対応

| 段 | 工程スキル | 手順骨格 (正典) |
| --- | --- | --- |
| 設計 | `ado-design` | `../../hotl-loop/references/stages/design.md` |
| 実装 | `ado-implement` | `../../hotl-loop/references/stages/implement.md` |
| レビュー | `ado-review` | `../../hotl-loop/references/stages/review.md` |
| 修正 | `ado-fix` | `../../hotl-loop/references/stages/fix.md` |

支援工程は正典の「調査」(手順は `workflows/research.md`)に加えて、ADO 固有に
**ビルド調査**がある: ビルドが失敗しているとき、`../SKILL.md` の「ビルド」の手順で
失敗ステップと原因を特定する。支援工程は成果物を先へ渡さず、呼んだ段に戻る。

## 判定の ADO 固有注意

依頼の中の識別子は、判定の前に ADO に引き当てる。数字だけの名前を持つファイル
(`2251.md` など)や裸の数字は作業アイテム ID であることがあるので、`wit get` で
確認してから段を決める。引き当てずに判定すると、ループの外の作業として扱ってしまう。

## 「人間が握る制御点」の ADO 形

正典の一覧を Azure DevOps ではこう実装する。

- 新しい成果物の発行 = 作業アイテムの起票(`wit create`)と Pull Request の作成
  (`pr create`)。本文承認を得てから行い、承認を得られない非対話の実行では
  `pr create` を既定のまま(ドラフト)にして公開判断を人間に残す
- チケットの状態 = `System.State`。触らない。いつ誰が状態を動かすかは組織の運用で
  決まっている
- マージ・完了・破棄・投票、指摘スレッドの解決済み化はしない(該当コマンドは
  `ado.py` に意図的に実装していない)
