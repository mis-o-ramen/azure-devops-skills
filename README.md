# azure-devops-skills

オンプレミスの **Azure DevOps Server 2022** を操作するエージェントスキル。作業アイテム、
プルリクエスト、ビルドパイプラインを扱う。

## 構成

```
.claude/skills/azure-devops/
├── SKILL.md                  # エージェントが読み込むエントリポイント
├── scripts/ado.py            # REST クライアント。Python 3 標準ライブラリのみ
└── references/
    ├── recipes.md            # WIQL の書き方、頻出フロー、トラブルシュート
    └── fields/               # 生成されるフィールド定義（コミットしない）
```

## Claude と GitHub Copilot の両方で動く

1 コピーで両対応する。GitHub Copilot はスキルを `.github/skills`、`.claude/skills`、
`.agents/skills` から読み込むため、上の構成がそのまま Copilot coding agent・Copilot CLI・
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

**macOS / Linux** — ディレクトリ単位でシンボリックリンクを張る。`git pull` がそのまま
反映される。

```sh
mkdir -p ~/.claude/skills ~/.copilot/skills
ln -s ~/src/azure-devops-skills/.claude/skills/azure-devops ~/.claude/skills/azure-devops
ln -s ~/src/azure-devops-skills/.claude/skills/azure-devops ~/.copilot/skills/azure-devops
```

**Windows（PowerShell）** — シンボリックリンクには開発者モードか管理者権限が要る。

```powershell
New-Item -ItemType SymbolicLink -Path "$HOME\.claude\skills\azure-devops" `
         -Target "$HOME\src\azure-devops-skills\.claude\skills\azure-devops"
```

権限が得られない場合はコピーでもよい。ただし `git pull` のたびにコピーし直す必要があり、
生成済みのフィールド定義はコピー先に置かれるため上書きに注意する。

```powershell
Copy-Item -Recurse -Force "$HOME\src\azure-devops-skills\.claude\skills\azure-devops" `
          "$HOME\.claude\skills\"
```

ファイル単位のリンクやコピーにはしない。スクリプトは自身の位置を基準にフィールド定義を
書き出すため、ディレクトリ構造が保たれている必要がある。

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

## 生成物はコミットしない

`references/fields/` に生成されるファイルには、サーバ URL・プロジェクト名・社内の
プロセステンプレートの定義が含まれる。`.gitignore` で除外済みで、各実行環境のローカルに
置いたままにする。プロセステンプレートを変更した後は再生成する。

## 対応範囲

| 含む | 含まない |
| --- | --- |
| 作業アイテム: WIQL 検索、参照、作成、更新、コメント、フィールドと State の取得 | 添付ファイル、リンク階層、プロセステンプレートの編集 |
| プルリクエスト: 一覧、参照、レビュースレッド、コメント、作成 | 完了、破棄、投票、ポリシー上書き |
| ビルド: 定義、実行履歴、状態、失敗ステップのログ | 実行トリガ、変数グループ、承認 |
| その他のエンドポイントは `ado.py request` から | Git 操作 — `git` CLI を使う |

取り消せない操作は意図的に外してある。該当する場面では URL を提示し、人間が判断する。
