# azure-devops-skills

オンプレミスの **Azure DevOps Server 2022** を使った開発を、人間が承認点で監督する
ループ（human-on-the-loop）として回すためのエージェントスキル。このリポジトリは
HOTL ループの **Azure DevOps 手足**で、持つのは hotl インターフェースの ADO
バックエンドと ADO 固有の能力だけ。ループの定義・工程スキル・出力規約・
インターフェース仕様の正典はコアリポジトリ
[hotl-core](https://github.com/mis-o-ramen/hotl-core) にあり、**ここにはコピーを
置かない** — hotl-core を並べて clone し、両方のスキルを同じディレクトリに symlink で
束ねて使う（導入手順を参照）。工程スキルはサービス非依存の `hotl` コマンドだけを
使い、その ADO への変換をこのリポジトリのバックエンドが行う。

| スキル | ループでの位置 | 何をするか |
| --- | --- | --- |
| `azure-devops` | 能力層（段を持たない） | **hotl バックエンド** (`scripts/hotl-backend` → `ado.py`)、REST クライアント、調査・ビルド調査の支援手順、ADO 固有差分 (`references/loop.md`) |
| `hotl-design` / `hotl-implement` / `hotl-review` / `hotl-fix` | コア（hotl-core 側） | 段ごとの工程スキル。発火語彙は「作業アイテムにしたい」「2251 を実装して」にも対応 |
| `hotl-research` | コア（hotl-core 側） | 支援工程: 調べて作業アイテムに報告する |
| `hotl-ops` / `hotl-loop` | コア（hotl-core 側） | 操作の統一インターフェースと、ループの定義 |
| `output-contract` ほか / `coding-rules` | コア（hotl-core 側） | 出力・応答・成果物の共通規約 3 スキルと、規約整備の道具 |

## 構成

```
.claude/skills/
├── azure-devops/             # 能力層 = この手足の本体
│   ├── SKILL.md              # ADO の操作コマンドと、その使い分け
│   ├── scripts/
│   │   ├── hotl-backend      # hotl インターフェースの ADO 実装 (ado.py へ変換)
│   │   └── ado.py            # REST クライアント。Python 3 標準ライブラリのみ
│   └── references/
│       ├── loop.md           # ADO 固有差分 (承認点の形・ビルド調査・ID 引き当て)
│       ├── recipes.md        # WIQL の書き方、頻出フロー、トラブルシュート
│       └── fields/           # 生成されるフィールド定義（コミットしない）
└── (これだけ)

(工程スキル hotl-{design,implement,review,fix}、支援工程 hotl-research、
 インターフェース hotl-ops、ループ定義 hotl-loop、規約 3 スキル、coding-rules は
 hotl-core リポジトリにあり、導入手順で同じ skills ディレクトリに symlink で並ぶ)
```

## コア・バックエンド・能力を分ける

| 層 | 置き場所 | 何を書くか |
| --- | --- | --- |
| コア | hotl-core（並置 clone） | ループの定義・工程スキル・インターフェース仕様・共通規約。サービス名を消しても成り立つもの |
| バックエンド | `azure-devops/scripts/hotl-backend` | `hotl` コマンドの ADO への変換。型の対応・フィールドの格納・ドラフト既定はここがコードで守る |
| 差分 | `azure-devops/references/loop.md` | コマンドに吸収されない ADO 固有の規則 (承認点の形・ビルド調査・ID 引き当て) |
| 能力 | `azure-devops` の `SKILL.md` と `scripts/ado.py` | ADO を操作する方法。`hotl raw` の先で使う |

工程の語彙と手順はコアの工程スキルが持つ (「実装したい」「作業アイテムにしたい」は
そちらで発火する)。`azure-devops` は ADO の名詞（作業アイテム、PR、WIQL…）だけで
発火する能力層に徹する。

スキルは**両リポジトリ分を全部まとめて同じディレクトリに**配置する。工程スキルは
`../hotl-ops/` を、能力層内の文書は互いを兄弟参照するため、一部だけ配置すると
参照が壊れる。

ループの段に対応しない手順はこのリポジトリに置かない (規約整備の道具 `coding-rules`
もサービス非依存のため hotl-core 側にある)。

## Claude と GitHub Copilot の両方で動く

1 コピーで両対応する。GitHub Copilot はスキルを `.github/skills`、`.claude/skills`、
`.agents/skills` から読み込むため、この構成がそのまま Copilot coding agent・Copilot CLI・
VS Code の agent mode で認識される。Claude Code も同じディレクトリを読む。

そのため `SKILL.md` は道具非依存に書いてある。同梱スクリプトの実行を指示するだけで、
特定ベンダのツール名には一切触れない。

## 導入

### 1. 実行環境に clone する（2 リポジトリ）

Azure DevOps Server に到達できる環境（社内の開発マシンなど）に、このリポジトリと
コア（hotl-core）を並べて clone する。

```sh
git clone <このリポジトリ> ~/src/azure-devops-skills
git clone https://github.com/mis-o-ramen/hotl-core ~/src/hotl-core
```

### 2. スキルをホームディレクトリに配置する

リポジトリを clone しただけでは、このリポジトリを開いているときしかスキルが発火しない。
実際には別のコードリポジトリで作業しながら使うため、ホームディレクトリ配下に、
**両リポジトリのスキルを同じディレクトリへ**配置する。

配置は 2 段になる。**先にコアのスキルをこのリポジトリの skills ディレクトリへリンクし
(untracked、`.gitignore` 済み)、次にそこからホームへリンクする。** 能力層の文書は
`../../hotl-ops/…` の兄弟参照を使うが、ディレクトリ symlink 越しの `..` はリンク先の親に
解決されるため、コアのリンクは実体のある `.claude/skills/` の中に置く必要がある。
ホームへ直接 2 系統をリンクする配置では参照が壊れる。

**macOS / Linux** — `git pull` がそのまま反映される（コアの改訂も pull だけで届く）。

```sh
# 1. コアのスキルをこのリポジトリの skills ディレクトリへ (untracked)
for s in hotl-loop hotl-ops hotl-design hotl-implement hotl-review hotl-fix hotl-research \
         output-contract consult-response artifact-writing coding-rules; do
  ln -sfn ~/src/hotl-core/plugins/$s/skills/$s \
          ~/src/azure-devops-skills/.claude/skills/$s
done

# 2. 全スキル (ADO 実体 + コアリンク) をホームへ
mkdir -p ~/.claude/skills ~/.copilot/skills
for s in azure-devops \
         hotl-loop hotl-ops hotl-design hotl-implement hotl-review hotl-fix hotl-research \
         output-contract consult-response artifact-writing coding-rules; do
  ln -s ~/src/azure-devops-skills/.claude/skills/$s ~/.claude/skills/$s
  ln -s ~/src/azure-devops-skills/.claude/skills/$s ~/.copilot/skills/$s
done
```

**Windows（PowerShell）** — シンボリックリンクには開発者モードか管理者権限が要る。

```powershell
foreach ($s in "hotl-loop", "hotl-ops", "hotl-design", "hotl-implement", "hotl-review",
               "hotl-fix", "hotl-research", "output-contract", "consult-response",
               "artifact-writing", "coding-rules") {
  New-Item -Force -ItemType SymbolicLink `
           -Path "$HOME\src\azure-devops-skills\.claude\skills\$s" `
           -Target "$HOME\src\hotl-core\plugins\$s\skills\$s"
}
foreach ($s in "azure-devops",
               "hotl-loop", "hotl-ops", "hotl-design", "hotl-implement", "hotl-review",
               "hotl-fix", "hotl-research", "output-contract", "consult-response",
               "artifact-writing", "coding-rules") {
  New-Item -ItemType SymbolicLink -Path "$HOME\.claude\skills\$s" `
           -Target "$HOME\src\azure-devops-skills\.claude\skills\$s"
}
```

権限が得られない場合はコピーでもよい。ただし `git pull` のたびにコピーし直す必要があり、
生成済みのフィールド定義はコピー先に置かれるため上書きに注意する。

```powershell
foreach ($s in "hotl-loop", "hotl-ops", "hotl-design", "hotl-implement", "hotl-review",
               "hotl-fix", "hotl-research", "output-contract", "consult-response",
               "artifact-writing", "coding-rules") {
  Copy-Item -Recurse -Force "$HOME\src\hotl-core\plugins\$s\skills\$s" `
            "$HOME\src\azure-devops-skills\.claude\skills\$s"
}
Copy-Item -Recurse -Force "$HOME\src\azure-devops-skills\.claude\skills\*" `
          "$HOME\.claude\skills\"
```

ファイル単位のリンクやコピーにはしない。スクリプトは自身の位置を基準にフィールド定義を
書き出すため、ディレクトリ構造が保たれている必要がある。また、スキルは**両リポジトリ分を
全部まとめて同じディレクトリに**配置する。hotl のディスパッチャはバックエンド
(`azure-devops/scripts/hotl-backend`) を同じディレクトリから探すため、一部だけ
配置すると解決に失敗する。

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
`hotl-review` スキル (コア) と `hotl pr diff` を参照。
