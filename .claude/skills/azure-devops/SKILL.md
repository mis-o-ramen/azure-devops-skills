---
name: azure-devops
description: オンプレミスの Azure DevOps Server 2022 を REST API 経由で操作する能力層。作業アイテム（ユーザーストーリー、フィーチャー、バグ、タスク、PBI）の検索・参照・作成・更新・コメント、受け入れ基準など型ごとに異なるフィールドと State の取得、プルリクエストの参照・スレッド・コメント・作成、PR に紐づく作業アイテムの取得、失敗したビルドパイプラインの調査、調査結果の報告。ユーザーが作業アイテム、ワークアイテム、ユーザーストーリー、バックログ、スプリント、イテレーション、WIQL、プルリクエスト、PR、ビルド、パイプライン、Azure DevOps、ADO、TFS に言及したときに使う。設計・実装・レビュー・指摘対応の各工程は兄弟スキル issue-design / issue-implement / pr-review / pr-fix が持ち、いずれもこのスキルを能力層として使う。Operate a self-hosted Azure DevOps / TFS server; the process stages live in the sibling stage skills (issue-design, issue-implement, pr-review, pr-fix); read the stage skill first.
---

# Azure DevOps Server（オンプレミス）

**依頼が工程（設計・実装・レビュー・指摘対応）なら、先にその工程スキルを読む。** このスキルは
操作の方法だけを持ち、ブランチを切る・テストを先に書く・承認を得てから PR を作る、といった
工程の手順を持たない。工程スキルを読まずに進めると、それらが丸ごと抜けたまま実装が始まる。

| 依頼 | 先に読むスキル |
| --- | --- |
| アイデアを作業アイテムに落とす（設計。「設計したい」「起票したい」） | `issue-design` |
| 作業アイテムを実装する（「〜に着手」「〜を実装して」） | `issue-implement` |
| プルリクエストをレビューする（「レビューして」「PR を見て」） | `pr-review` |
| レビュー指摘に対応する（「指摘に対応して」「スレッドを直して」） | `pr-fix` |

工程スキルが見当たらないときは、コードにもブランチにも触らずに止まり、スキルが配置されて
いないことを依頼者に伝える（README「導入」の手順で配置し直す）。このスキルだけで工程を
代行しない。

すべての操作は `scripts/ado.py` を通す（`python3 scripts/ado.py …`。`python3` がなければ
`python`）。以下のパスはこのスキルのディレクトリからの相対パス。

Git の操作そのものはスコープ外。clone / diff / branch / commit は `git` CLI を使い、
`scripts/ado.py` が扱うのは REST API でしか取得できないものに限る。ブランチ名と
コミットメッセージの規約は `git-conventions` スキルにある。`references/` は全段が実行時に
読む共通の文書の置き場で、REST の機能の範囲とは別（`loop.md`・`writing.md`）。

## セットアップ

4 つの環境変数で動作する。

| 変数 | 必須 | 内容 |
| --- | --- | --- |
| `ADO_ORG_URL` | 必須 | コレクション URL。例 `https://tfs.example.com/tfs/DefaultCollection` |
| `ADO_PAT` | 必須 | 個人用アクセストークン |
| `ADO_PROJECT` | 任意 | 既定のチームプロジェクト（`--project` で個別に上書き可） |
| `ADO_CA_BUNDLE` | 任意 | サーバ証明書が社内 CA 発行の場合の CA バンドルのパス |

何よりも先に疎通を確認する。

```
python3 scripts/ado.py wit types
```

作業アイテム型の一覧が返れば、URL・PAT・TLS 信頼のすべてが通っている。返らない場合は
`references/recipes.md` の「トラブルシュート」を見る。

## 最初にフィールドを調べる

作業アイテムのフィールドは型ごと・プロジェクトごとに異なる。「受け入れ基準」は
ユーザーストーリーにはあるがバグやタスクにはない。さらにオンプレミスのプロセステンプレート
は改造されていることが多く、このサーバのフィールド構成が既定の Agile テンプレートと同じとは
限らない。

参照名を推測しない。そのセッションでまだ扱っていない型の作業アイテムを作成・更新する前に、
次の順で確認する。

1. `references/fields/` に `<プロジェクト>.<型>.md` があれば読む。
2. なければ生成する。
   ```
   python3 scripts/ado.py wit describe-type --type "User Story" --save
   ```
   表示名・参照名・データ型・必須フラグ・許可値の表と、その型で有効な State の一覧が
   `references/fields/` に書き出される。

この表から 2 つの決まりが導かれる。

- データ型が `html` のフィールド（`System.Description`、
  `Microsoft.VSTS.Common.AcceptanceCriteria`、`Microsoft.VSTS.TCM.ReproSteps`）は、
  素の改行が失われる。`--field-multiline` で書き込む（エスケープして改行を `<br>` に
  変換する）。それ以外の型には `--field` を使う。
- `System.State` はその型に定義された State しか受け付けない。
  `New/Active/Resolved/Closed` だと決めつけない。

`html` 型のフィールドは、読み出すと HTML のまま返る。それを `--field-multiline` に渡すと
二重にエスケープされるため、**既存の本文を読んで書き戻す使い方はできない**。本文は新規作成
時にまとめて書き、後からの追記はコメント（`wit comment`）で行う。

生成済みのファイルはプロセステンプレートの変更後に古くなる。存在しないフィールドを示す
HTTP 400 で書き込みが失敗したら再生成する。

生成されたファイルはコミットしない（`.gitignore` で除外済み。理由は
`references/fields/README.md`）。

## 作業アイテム

```
wit types                                 # プロジェクトで使える型の一覧
wit describe-type --type "Bug" --save     # フィールド・State・許可値
wit query --wiql "SELECT …"               # WIQL 検索。ID 解決とフィールド取得まで一度に行う
wit get 1234 5678 [--relations]           # ID 指定で全フィールドを取得
wit create --type "User Story" --title …  # 作成
wit update 1234 --assign "…"              # 更新（State 以外のフィールド）
wit set-state 1234 Active                 # State の変更。人間の明示の指示があるときだけ
wit comment 1234 --text "…"               # コメントを追加
wit comments 1234                         # ディスカッションを読む
```

`wit create` と `wit update` の `--parent <id>` で親子リンクを張る。作業アイテムは親を
1 つしか持てないため、`wit update --parent` は既存の親を同じパッチで外して付け替える
（既にその親なら何もしない）。親子以外のリンク（Related、Duplicate など）は `request` を使う。

`--field`、`--field-multiline`、`--title`、`--text`、`--description`、`--wiql` は
`@パス` を渡すとファイルから値を読む。長い文章や複数行はシェルのクォートと戦わずにこちらを
使う。

`wit query` は WIQL の `SELECT` 句に書いた列を返す。取得後に絞り込むのではなく `SELECT` を
絞る。大きなバックログに対する広いクエリは出力が膨れる。WIQL の書き方は
`references/recipes.md` を参照。

## プルリクエスト

```
pr list --repo <repo> [--status active] [--target main]
pr get <id> --repo <repo>
pr threads <id> --repo <repo> [--unresolved-only]
pr workitems <id> --repo <repo>           # 紐づく作業アイテムをフィールドごと取得
pr comment <id> --repo <repo> --text "…" [--file path --line N] [--thread N]
pr create --repo <repo> --source <branch> --target <branch> --title "…" [--publish]
```

`pr create` は既定で**ドラフト**として作る。公開はレビュアーへの通知を伴い、ここからは
取り消せないため、`--publish` を付けるのは本文の承認を得たときだけ。作成そのものも
`references/loop.md` の承認点で、ドラフトでも承認なしには作らない。

`--thread` は既存スレッドへの返信、`--file`/`--line` は差分の行に紐づく新規スレッド、
どちらも指定しなければトップレベルの新規スレッドになる。ブランチ名の `refs/heads/` は
省略できる。

プルリクエストの完了・破棄、投票、ブランチポリシーの上書きは意図的に実装していない。
エージェント側から取り消せないため、プルリクエストの URL を提示して人間に判断を委ねる。

## ビルド

```
build definitions [--name <フィルタ>]
build list [--definition <id>] [--result failed] [--branch main]
build get <id>
build logs <id> [--fetch] [--tail 200] [--log <logId>]
```

`build logs <id>` 単体で、失敗したステップとそこに記録されたエラーメッセージを一覧する。
原因究明はたいていこれで足りる。メッセージが具体性を欠くときだけ `--fetch` を足すと、
失敗した各ステップのログ末尾 `--tail` 行を取得する。ログ全体は巨大なので、`--tail 0` を
渡すのではなく `--tail` を段階的に増やす。

ビルドの実行トリガはスコープ外。

## 工程スキルが引く操作

工程スキル (`issue-design`・`issue-implement`・`pr-review`・`pr-fix`) はすべて GitHub と
共用で、基盤ごとに違う操作を「チケットを読む」のような操作名で書いている。この節がその Azure DevOps での実行方法。操作名の一覧と契約は
中央リポジトリ ai-workflows の `docs/platform-ops.md` にあり、ここはそれを実装する。
工程スキルの「チケット」は作業アイテム、「受け入れ条件」は受け入れ基準を指す。

### チケットを読む

```
wit get <id> --relations
wit comments <id>
```

受け入れ条件がどのフィールドにあるかは型で決まる。ユーザーストーリーなら
`Microsoft.VSTS.Common.AcceptanceCriteria`、バグなら `Microsoft.VSTS.TCM.ReproSteps` に
入っていることが多いが、参照名を推測せず「最初にフィールドを調べる」の手順で確認する。

### 親チケットを読む

`wit get <id> --relations` の `relations` のうち `System.LinkTypes.Hierarchy-Reverse` が
親。その ID を `wit get` で読む。無ければ親は無い。

### チケットを探す

```
wit query --wiql "SELECT [System.Id], [System.Title], [System.State] FROM WorkItems WHERE [System.TeamProject] = @project AND [System.Title] CONTAINS '<キーワード>'"
```

閉じた作業アイテムも State で絞らずに含める。WIQL の書き方は `references/recipes.md`。

### チケットを起票する

型は機能ならユーザーストーリー (プロセスによっては PBI)、バグならバグ。書く前に
「最初にフィールドを調べる」でその型のフィールドを確認する。設計の工程の要素は次に置く。

- タイトル → `--title`
- 背景・目的、スコープ外、設計判断 → `System.Description` (`--description`)
- 受け入れ条件 → 受け入れ基準のフィールド (ユーザーストーリーなら
  `Microsoft.VSTS.Common.AcceptanceCriteria`)。`--field-multiline` で 1 件 1 行に書く

```
wit create --type "User Story" --title "…" --description @body.md \
  --field-multiline Microsoft.VSTS.Common.AcceptanceCriteria=@criteria.md
```

`html` 型のフィールドは読み戻して書き直せない (「最初にフィールドを調べる」)。起点の
作業アイテムがあっても書き換えず、新しく起票して、起点に `wit comment` で起票した ID と
URL を 1 行ずつ残す。起票後の本文の修正は利かないので、起票前に承認を得た本文だけを書く。

### チケットを分割する

フィーチャーを親にして子ストーリーに分ける。親フィーチャーから先に作り、子は
`--parent <親id>` でぶら下げる。子の起票まで設計の工程で行う。子の間に実装順の依存が
あれば親の説明に 1 行で書く。

```
wit create --type "Feature" --title "…" --description @parent.md
wit create --type "User Story" --title "…" --parent <親id> …
```

### チケットにコメントする

```
wit comment <id> --text @comment.md
```

プレーンテキストとして入る。表・折りたたみは使えない (`references/writing.md`)。
記号で区切って 1 行にまとめ、長い根拠はプルリクエストに置く。

### PR を作る

```
pr create --repo <repo> --source <ソース> --target <ターゲット> \
  --title "…" --description @body.md --work-item <id> --publish
```

`--work-item` が作業アイテムへの紐づけ。レビューの段は `pr workitems` でここから
受け入れ基準を読むので、省かない。`--publish` を付けるのは本文の承認を得たときだけ
(「プルリクエスト」の節)。PR テンプレートは `.azuredevops/pull_request_template.md`、
無ければ `.github/pull_request_template.md`。

### PR を読む

```
pr get <id> --repo <repo>
```

`sourceRefName` がソースブランチ、`targetRefName` がターゲットブランチ。どちらも
`refs/heads/` を外して使う。`lastMergeSourceCommit` がソース側の最新コミット。

### 紐づくチケットを読む

```
pr workitems <id> --repo <repo>
```

紐づく作業アイテムがフィールドごと返る。受け入れ基準は
`Microsoft.VSTS.Common.AcceptanceCriteria` (型によっては別のフィールド。「チケットを
読む」と同じく参照名を推測しない)。コメントは `wit comments <id>` で読む。空の配列なら
紐づきは無い。

### PR の指摘を読む

```
pr threads <id> --repo <repo>
```

差分の行に付いたスレッドとトップレベルのスレッドが、解決状態付きで返る。
`--unresolved-only` で未解決だけに絞れるが、解決済みのスレッドに人間の判断が残って
いることがあるので、対応方針に迷ったら絞らずに読む。

### PR にコメントする

```
pr comment <id> --repo <repo> --text @report.md
```

トップレベルの新規スレッドとして入る。Markdown が効き、表・箇条書きを使える
(`references/writing.md`)。スレッドを解決済みにしない。

### PR の行にコメントする

```
pr comment <id> --repo <repo> --file <パス> --line <N> --text @finding.md
```

差分の行に紐づく新規スレッドになる。`--line` は変更後のファイルの行番号。

`System.State` は変えない。

## 工程の作業はこのスキルでは進めない

開発ループの段にあたる依頼は、冒頭の表の工程スキル（同じ skills ディレクトリ直下）に
手順がある。

段の定義と、どの段にいるかの判定は `references/loop.md` にある。

調査して報告する依頼は工程ではなく支援作業で、手順は
`references/workflows/research.md` に置いてある。

報告の書き方は `references/writing.md` に共通で置いてある。各手順はそこに固有の上限を
足す。

## それ以外の操作

`scripts/ado.py request <METHOD> <パス>` で任意のエンドポイントを直接呼べる。認証・
コレクション URL・TLS・`api-version` は処理済み。

```
python3 scripts/ado.py request GET /wit/workitems/1234 --query '$expand=relations'
python3 scripts/ado.py request POST /wit/wiql --data @query.json
```

パスは `_apis` からの相対。`--collection-level` でプロジェクト部分を外し、
プレビュー版が必要なルートには `--api-version-override` を使う。

GET 以外の `request` は、実装済みコマンドが意図的に外している操作にも到達できる。到達
できることは許可ではない。プルリクエストの完了・破棄・投票と、指摘スレッドの解決済み化は、
承認を求めてでも代行しない（`references/loop.md`「人間が握る制御点」）。URL を提示して
人間が行う。それ以外の書き込みの `request` は、目的の操作を示して人間の承認を得てから使う。

## 参照

- `references/loop.md` — 開発ループの定義。段・入口条件・成果物・人間の承認点
- `references/writing.md` — 報告の書き方と、投稿先ごとの制約
- `references/workflows/research.md` — 調査して報告する手順
- `references/recipes.md` — WIQL の書き方、頻出フロー、トラブルシュート
- `references/fields/` — 生成されたプロジェクト×型ごとのフィールド定義
