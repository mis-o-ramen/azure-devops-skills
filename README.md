# azure-devops-skills

オンプレミスの **Azure DevOps Server 2022** を使った開発を、人間が承認点で監督する
ループ（human-on-the-loop）として回すためのエージェントスキル。ループの定義は
[`loop.md`](.claude/skills/azure-devops/references/loop.md) にあり、各スキルと手順は
その段に仕える。実行時にスキルから参照できるよう、定義は能力層スキルの中に置いてある。

| スキル | ループでの位置 | 何をするか |
| --- | --- | --- |
| `issue-design` | 設計の段 | アイデアを、受け入れ基準まで埋まった作業アイテムに落とす（ai-workflows から配布） |
| `issue-implement` | 実装の段 | 作業アイテムを実装し、プルリクエストを作る（ai-workflows から配布） |
| `ado-review` | レビューの段 | プルリクエストをレビューし、優先度付きの指摘を投稿する |
| `pr-fix` | 修正の段 | レビュー指摘に対応し、同じブランチに push する（ai-workflows から配布） |
| `azure-devops` | 能力層（段を持たない） | ADO の操作方法。REST クライアントと、調査などの支援手順 |
| `coding-rules` | ループ外 | プロジェクトのコーディング規約を整備する |
| `output-contract` / `artifact-writing` / `git-conventions` | 共通規約 | 共用の工程スキルが読む出力・成果物・git の規約（ai-workflows から配布） |

## 構成

```
.claude/skills/
├── issue-design/SKILL.md     # 設計: アイデアを作業アイテムに落とす（配布物）
├── issue-implement/SKILL.md  # 実装: 作業アイテムを実装する（配布物）
├── ado-review/SKILL.md       # レビュー: プルリクエストをレビューする
├── pr-fix/SKILL.md           # 修正: レビュー指摘に対応する（配布物）
├── azure-devops/             # 能力層。工程スキルはここを兄弟参照する
│   ├── SKILL.md              # ADO の操作コマンドと、その使い分け
│   ├── scripts/ado.py        # REST クライアント。Python 3 標準ライブラリのみ
│   └── references/
│       ├── loop.md           # ループの定義。段・入口条件・成果物・人間の承認点
│       ├── writing.md        # 報告の書き方（全工程の共通規約）
│       ├── git.md            # ブランチ名とコミットメッセージの規約（実装・修正の段）
│       ├── workflows/
│       │   └── research.md   # 支援工程: 調査して報告する
│       ├── recipes.md        # WIQL の書き方、頻出フロー、トラブルシュート
│       └── fields/           # 生成されるフィールド定義（コミットしない）
├── coding-rules/
│   └── SKILL.md              # 規約の抽出手順と、埋める欄の定義
├── output-contract/          # 配布物: 出力規約
├── artifact-writing/         # 配布物: 成果物の記述規約
├── git-conventions/          # 配布物: ブランチ名とコミットメッセージの規約
└── README.md                 # 配布物の一覧（自動生成）

scripts/
├── install.sh                # スキルをホームディレクトリに配置する（macOS / Linux）
└── install.ps1               # 同（Windows）
```

## ai-workflows と共用する工程スキル

GitHub 向けの中央リポジトリ ai-workflows と、段の定義・手順は同じ。基盤に依存しない
書き方にした工程スキルは ai-workflows を正典とし、このリポジトリへはコピーで配る。
配布物は手で編集しない。直すときは ai-workflows を直して配り直す。

```sh
cd ~/src/azure-devops-skills
/path/to/ai-workflows/scripts/sync-skills.sh \
  --only issue-design,issue-implement,pr-fix,output-contract,artifact-writing,git-conventions
```

共用の工程スキルは、基盤ごとに違う操作を「チケットを読む」「PR を作る」のような操作名で
書いている。Azure DevOps での実行方法は `azure-devops` の `SKILL.md`「工程スキルが引く
操作」が持つ。操作名の契約は ai-workflows の `docs/platform-ops.md`。

## 工程と能力を分ける

スキルの境界は `loop.md` の段に従う。

| 層 | 置き場所 | 何を書くか |
| --- | --- | --- |
| 工程 | 段スキル `ado-review`、共用の `issue-design` / `issue-implement` / `pr-fix` | その段の入口条件と手順。段固有の優先度・出力規約・上限 |
| 共通 | `azure-devops/references/writing.md` | 報告の書き方。各段はここに固有の上限を足す |
| 共通 | `azure-devops/references/git.md` | ブランチ名とコミットメッセージの規約。対象リポジトリの規約が優先 |
| 能力 | `azure-devops` の `SKILL.md` と `scripts/ado.py` | ADO を操作する方法。コマンドと、その使い分け。共用の工程スキルが引く操作の実装 |

工程を語彙に持つのは段スキルの description だけにする。ユーザーの依頼は「設計したい」
「実装に着手」といった工程の言葉で来るので、発火の語彙を工程側に寄せ、`azure-devops` は
ADO の名詞（作業アイテム、PR、WIQL…）だけで発火する能力層に徹する。

段スキルは能力層を `../azure-devops/` の兄弟参照で使う。ディレクトリ名を変えたり、
一部のスキルだけを配置したりすると、この参照が壊れる。

ループの段に対応しない手順はこのリポジトリに置かない。`coding-rules` はループの外だが、
実装の段が読む `CLAUDE.md` を整備する道具としてここに同居している。

## Claude と GitHub Copilot の両方で動く

1 コピーで両対応する。GitHub Copilot はスキルを `.github/skills`、`.claude/skills`、
`.agents/skills` から読み込むため、この構成がそのまま Copilot coding agent・Copilot CLI・
VS Code の agent mode で認識される。Claude Code も同じディレクトリを読む。

そのため `SKILL.md` は道具非依存に書いてある。同梱スクリプトの実行を指示するだけで、
特定ベンダのツール名には一切触れない。

## 導入

### 1. 実行環境に clone する

Azure DevOps Server に到達できる環境（社内の開発マシンなど）に clone する。

```sh
git clone <このリポジトリ> ~/src/azure-devops-skills
```

### 2. スキルをホームディレクトリに配置する

リポジトリを clone しただけでは、このリポジトリを開いているときしかスキルが発火しない。
実際には別のコードリポジトリで作業しながら使うため、ホームディレクトリ配下に配置する。

付属のスクリプトが `.claude/skills/` 直下のスキルをすべて、ディレクトリ単位の
シンボリックリンクで `~/.claude/skills`・`~/.copilot/skills`・`~/.agents/skills` に張る。`git pull` が
そのまま反映される。

```sh
~/src/azure-devops-skills/scripts/install.sh          # macOS / Linux
```

```powershell
# Windows。シンボリックリンクには開発者モードか管理者権限が要る
powershell -ExecutionPolicy Bypass -File $HOME\src\azure-devops-skills\scripts\install.ps1
```

**スキルが増えた・減った・改名された `git pull` の後は、必ずもう一度実行する。**
リンクはスキルごとに張るので、新しいスキルは実行するまで配置されない。エージェントからは
「そんなスキルは無い」に見え、工程の手順を読まずに能力層だけで作業を始める。スクリプトは
何度実行してもよく、このリポジトリを指したまま切れたリンクは外す。

権限が得られない場合はコピーでもよい。ただし `git pull` のたびにコピーし直す必要があり、
生成済みのフィールド定義はコピー先に置かれるため上書きに注意する。

```powershell
Copy-Item -Recurse -Force "$HOME\src\azure-devops-skills\.claude\skills\*" `
          "$HOME\.claude\skills\"
```

ファイル単位のリンクやコピーにはしない。スクリプトは自身の位置を基準にフィールド定義を
書き出すため、ディレクトリ構造が保たれている必要がある。また、スキルは全部まとめて
同じディレクトリに配置する。段スキル（`ado-*`）は能力層 `azure-devops` を兄弟参照する
ため、一部だけ配置すると参照が壊れる。

### 3. 環境変数を設定する

```sh
export ADO_ORG_URL="https://tfs.example.com/tfs/DefaultCollection"
export ADO_PAT="<個人用アクセストークン>"
export ADO_PROJECT="My Project"
export ADO_CA_BUNDLE="/etc/ssl/certs/internal-ca.pem"   # 社内 CA を使っている場合
```

必要な PAT のスコープ: *Work Items (read & write)*、プルリクエストには
*Code (read & write)*、ビルド調査には *Build (read)*。

### 4. 疎通とフィールド定義の生成

```sh
python3 ~/.claude/skills/azure-devops/scripts/ado.py wit types
python3 ~/.claude/skills/azure-devops/scripts/ado.py wit describe-type --type "User Story" --save
```

1 つ目で型の一覧が返れば、URL・PAT・TLS 信頼が通っている。2 つ目でそのサーバの実際の
フィールド定義が `references/fields/` に生成される。扱う型ぶんを実行しておく。

### 5. 実行時ゲートを設定する（推奨、Claude Code のみ）

スキルの規約は散文なので、遵守は確率的になる。取り返しの利かない操作は、実行時に
人間の確認を挟む permission 設定を重ねて決定論的に止める。`~/.claude/settings.json`
（またはプロジェクトの `.claude/settings.json`）に追加する。

```json
{
  "permissions": {
    "ask": [
      "Bash(* ado.py wit create *)",
      "Bash(* ado.py wit set-state *)",
      "Bash(* ado.py pr create *)",
      "Bash(* ado.py request POST *)",
      "Bash(* ado.py request PATCH *)",
      "Bash(* ado.py request PUT *)",
      "Bash(* ado.py request DELETE *)"
    ],
    "deny": [
      "Bash(git push --force*)",
      "Bash(git push -f*)"
    ]
  }
}
```

パターンの書式は Claude Code のバージョンで変わることがある。効いているかは
`/permissions` で確認する。

GitHub Copilot にはコマンド単位の確認機構が無いため、Copilot 実行を守るのは
ツール側の設計（取り消せない操作の非実装、`pr create` の既定ドラフト）と、サーバ側の
ブランチポリシーになる。ターゲットブランチへの直接 push の禁止は、エージェントの
規約ではなくブランチポリシー（PR 必須）で強制する。

## 生成物はコミットしない

`references/fields/` に生成されるファイルには、サーバ URL・プロジェクト名・社内の
プロセステンプレートの定義が含まれる。`.gitignore` で除外済みで、各実行環境のローカルに
置いたままにする。プロセステンプレートを変更した後は再生成する。

## ADO の対応範囲

| 含む | 含まない |
| --- | --- |
| 作業アイテム: WIQL 検索、参照、作成、更新、コメント、フィールドと State の取得 | 添付ファイル、リンク階層、プロセステンプレートの編集 |
| プルリクエスト: 一覧、参照、レビュースレッド、紐づく作業アイテム、コメント、作成 | 完了、破棄、投票、ポリシー上書き |
| ビルド: 定義、実行履歴、状態、失敗ステップのログ | 実行トリガ、変数グループ、承認 |
| その他のエンドポイントは `ado.py request` から | Git 操作 — `git` CLI を使う |

取り消せない操作は意図的に外してある。該当する場面では URL を提示し、人間が判断する。

レビュー時の差分取得も REST では行わない。ADS の REST が返すのは変更ファイルの一覧まで
なので、行単位の差分はローカル clone に対する `git diff` で取る。手順は
`ado-review` スキルを参照。
