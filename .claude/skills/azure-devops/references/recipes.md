# 実例とトラブルシュート

以下のコマンドはすべて `python3 scripts/ado.py` を前置する。

## WIQL

WIQL は SQL に似ているが制約がある。`JOIN` は使えず、`SELECT *` も使えない。返る列は
`SELECT` 句で決まる。クエリに書くのは表示名ではなく参照名。

自分に割り当てられた未クローズの作業アイテム:

```
wit query --wiql "SELECT [System.Id], [System.Title], [System.State], [System.WorkItemType]
FROM WorkItems
WHERE [System.TeamProject] = @project
  AND [System.AssignedTo] = @me
  AND [System.State] NOT IN ('Closed', 'Removed')
ORDER BY [System.ChangedDate] DESC"
```

現在のスプリントの全作業アイテム:

```
wit query --wiql "SELECT [System.Id], [System.Title], [System.State]
FROM WorkItems
WHERE [System.TeamProject] = @project
  AND [System.IterationPath] = @currentIteration
ORDER BY [System.Id]"
```

特定の作業アイテムの子（リンククエリ。クライアント側が対象 ID を抽出する）:

```
wit query --wiql "SELECT [System.Id] FROM WorkItemLinks
WHERE [Source].[System.Id] = 1234
  AND [System.Links.LinkType] = 'System.LinkTypes.Hierarchy-Forward'
MODE (MustContain)"
```

使えるマクロ: `@me`、`@project`、`@today`、`@currentIteration`。日付の計算は
`@today - 7` と書く。

長いクエリはファイルに置いて `--wiql @query.wiql` を渡す。

## 受け入れ基準つきのユーザーストーリーを作る

先にフィールド定義を生成し、HTML フィールドは `--field-markdown` で書き込む。

```
wit describe-type --type "User Story" --save

wit create --type "User Story" \
  --title "請求書を CSV で一括エクスポートできる" \
  --field-markdown "System.Description=@description.md" \
  --field-markdown "Microsoft.VSTS.Common.AcceptanceCriteria=@criteria.md" \
  --field "Microsoft.VSTS.Scheduling.StoryPoints=5" \
  --area "MyProject\\Billing" \
  --iteration "MyProject\\Sprint 42"
```

`--field-markdown` は Markdown のうち見出し・箇条書き（入れ子を含む）・番号付きリスト・表・
コードブロック・インラインコード・強調・リンク・引用・水平線を HTML に変換する。対応していない
記法はエスケープされてそのまま残るため、崩れても本文は失われない。生の HTML を入れたい場合は
`--field` に渡す。

フィールド名は型によって異なる。既定の Agile テンプレートでよく使う参照名:

| フィールド | 参照名 | 対象の型 |
| --- | --- | --- |
| Description | `System.Description` | すべて |
| Acceptance Criteria（受け入れ基準） | `Microsoft.VSTS.Common.AcceptanceCriteria` | User Story |
| Repro Steps（再現手順） | `Microsoft.VSTS.TCM.ReproSteps` | Bug |
| System Info | `Microsoft.VSTS.TCM.SystemInfo` | Bug |
| Story Points | `Microsoft.VSTS.Scheduling.StoryPoints` | User Story |
| Effort | `Microsoft.VSTS.Scheduling.Effort` | Product Backlog Item |
| Remaining Work | `Microsoft.VSTS.Scheduling.RemainingWork` | Task |
| Priority | `Microsoft.VSTS.Common.Priority` | ほとんどの型 |
| Business Value | `Microsoft.VSTS.Common.BusinessValue` | Feature、Epic |

この表はあくまで当たりをつけるための目安で、答えではない。そのサーバでの正解は
`references/fields/` に生成されたファイル。

## レビュースレッドに返信する

```
pr threads 812 --repo billing-api --unresolved-only
```

各スレッドは `threadId`、紐づくファイルパスと行番号、コメント群を持つ。新しいスレッドを
立てるのではなく、レビュアーが開いたスレッドに返信する。

```
pr comment 812 --repo billing-api --thread 7 --text "最新のプッシュで修正しました。"
```

## 失敗したビルドを調査する

```
build list --result failed --top 5
build logs 9271
```

`build logs` はフラグなしで、失敗した各ステップとエージェントが記録したエラーを表示する。
それでは判断がつかないときだけ:

```
build logs 9271 --fetch --tail 300
```

## 作業アイテムをプルリクエストに紐づける

```
pr create --repo billing-api --source feature/csv-export --target main \
  --title "CSV 一括エクスポート" --description @pr-body.md --work-item 1234
```

## トラブルシュート

| 症状 | 原因 |
| --- | --- |
| `ADO_ORG_URL is not set` | コレクション URL が未設定。サーバのルートではなく、`/tfs/DefaultCollection` のようにコレクション名まで含める。 |
| HTTP 401、またはサインインの HTML ページが返る | PAT が誤っているか失効している。あるいはサーバ側で Basic 認証の PAT が無効化されている。 |
| HTTP 403 | PAT は有効だがスコープが足りない。作業アイテムの書き込みには *Work Items (read & write)*、プルリクエストのコメントには *Code (read & write)*、ビルドログには *Build (read)* が要る。 |
| 正しそうなパスで HTTP 404 | プロジェクトかコレクションが違うか、そのルートがプレビュー版の api-version を要求している。`request … --api-version-override 7.0-preview.3` で再試行する。 |
| 存在しないフィールドを示す HTTP 400 | その参照名がその作業アイテム型に存在しない。`wit describe-type --save` で再生成する。 |
| `CERTIFICATE_VERIFY_FAILED` | `ADO_CA_BUNDLE` に社内 CA のバンドルを指定する。`ADO_TLS_INSECURE=1` は検証を無効化する最終手段。 |
| 社内ホストへの接続が拒否される、またはタイムアウトする | `HTTPS_PROXY` が社内サーバにも適用されている。そのホストを `NO_PROXY` に追加する。 |
| コメントは通ったがディスカッションに出ない | `wit comment` は `System.History` に書き込み、作業アイテムのディスカッションに表示される。作業アイテムの ID を確認する。 |

## api-version

Azure DevOps Server 2022 が提供するのは `api-version=7.0` で、全コマンドが既定でこれを使う。
作業アイテムのコメントだけは `7.0-preview.3` でしか取得できず、`wit comments` は内部で
それを指定している。`7.1` 以降として文書化されているエンドポイントはこのサーバには存在
しないため、`7.0` か対応するプレビュー版を使う。
