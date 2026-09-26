#!/usr/bin/env bash
# スキルをホームディレクトリに配置する (macOS / Linux)。
#
#   ./scripts/install.sh
#
# .claude/skills/ 直下のスキルをすべて ~/.claude/skills・~/.copilot/skills・~/.agents/skills に
# ディレクトリ単位のシンボリックリンクで張る。何度実行してもよい。
# - スキルが増えたら張り、このリポジトリを指したまま切れたリンク (削除・改名された
#   スキル) は外す
# - 同名の実ディレクトリ (コピーで配置したもの) は触らずに警告する
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC="$REPO/.claude/skills"

for dest in "$HOME/.claude/skills" "$HOME/.copilot/skills" "$HOME/.agents/skills"; do
  mkdir -p "$dest"

  for link in "$dest"/*; do
    [[ -L "$link" && ! -e "$link" ]] || continue
    case "$(readlink "$link")" in
      "$SRC"/*) rm "$link"; echo "- $link (切れたリンクを外した)" ;;
    esac
  done

  for skill in "$SRC"/*/; do
    name="$(basename "$skill")"
    [[ -f "$skill/SKILL.md" ]] || continue
    target="$dest/$name"
    if [[ -e "$target" && ! -L "$target" ]]; then
      echo "! $target は実ディレクトリなので触らない (コピーで配置したなら消してから再実行する)"
      continue
    fi
    # -n: 既存のリンクをたどらず置き換える。付けないとリンク先のディレクトリの中に張られる
    ln -sfn "$SRC/$name" "$target"
    echo "✓ $target"
  done
done
