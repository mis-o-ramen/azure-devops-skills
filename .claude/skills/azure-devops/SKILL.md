---
name: azure-devops
description: オンプレミスの Azure DevOps Server 2022 を REST API 経由で操作する。作業アイテム（ユーザーストーリー、フィーチャー、バグ、タスク、PBI）の検索・参照・作成・更新、受け入れ基準など型ごとに異なるフィールドの取得、プルリクエストの参照・レビュー・コメント、PR に紐づく作業アイテムの取得、失敗したビルドパイプラインの調査。ユーザーが作業アイテム、ワークアイテム、ユーザーストーリー、バックログ、スプリント、イテレーション、WIQL、プルリクエスト、PR、コードレビュー、ビルド、パイプライン、Azure DevOps、ADO、TFS に言及したときに使う。Use for work items, pull requests and builds on a self-hosted Azure DevOps / TFS server.
---

# Azure DevOps Server（オンプレミス）

すべての操作は `scripts/ado.py` を通す（`python3 scripts/ado.py …`。`python3` がなければ
`python`）。以下のパスはこのスキルのディレクトリからの相対パス。

Git 操作はスコープ外。clone / diff / branch / commit は `git` CLI を使う。このスキルが
扱うのは REST API でしか取得できないものに限る。

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
wit update 1234 --state Active            # 更新
wit comment 1234 --text "…"               # コメントを追加
wit comments 1234                         # ディスカッションを読む
```

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
pr create --repo <repo> --source <branch> --target <branch> --title "…"
```

`--thread` は既存スレッドへの返信、`--file`/`--line` は差分の行に紐づく新規スレッド、
どちらも指定しなければトップレベルの新規スレッドになる。ブランチ名の `refs/heads/` は
省略できる。

プルリクエストの完了・破棄、投票、ブランチポリシーの上書きは意図的に実装していない。
エージェント側から取り消せないため、プルリクエストの URL を提示して人間に判断を委ねる。

### レビューする

レビューを求められたら、先に `references/workflows/pr-review.md` を読む。差分の取り方、
受け入れ基準との突き合わせ、指摘の優先度と書式、行アンカーのずれの検証まで、そこに
手順がある。

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

## それ以外の操作

`scripts/ado.py request <METHOD> <パス>` で任意のエンドポイントを直接呼べる。認証・
コレクション URL・TLS・`api-version` は処理済み。

```
python3 scripts/ado.py request GET /wit/workitems/1234 --query '$expand=relations'
python3 scripts/ado.py request POST /wit/wiql --data @query.json
```

パスは `_apis` からの相対。`--collection-level` でプロジェクト部分を外し、
プレビュー版が必要なルートには `--api-version-override` を使う。

## 参照

- `references/workflows/` — 判断を伴う手順（レビューなど）。該当する作業のときに読む
- `references/recipes.md` — WIQL の書き方、頻出フロー、トラブルシュート
- `references/fields/` — 生成されたプロジェクト×型ごとのフィールド定義
