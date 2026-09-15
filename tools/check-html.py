#!/usr/bin/env python3
"""作業アイテムに書き込んだ HTML が、そのまま読み戻せるかを確かめる。

`--field-markdown` が送った HTML と、サーバから取得した HTML を突き合わせる。
差分はサーバのサニタイザが書き換えた箇所であり、それがこのスクリプトの答え。

    python3 tools/check-html.py <作業アイテム id>
    python3 tools/check-html.py <id> --field Microsoft.VSTS.Common.AcceptanceCriteria
    python3 tools/check-html.py <id> --source 自前のテキスト.md

比較元は `tools/markdown-fixture.md`（`--source` で差し替え可）。先にそれを書き込んで
おくこと。

    python3 .claude/skills/azure-devops/scripts/ado.py wit create \
      --type "User Story" --title "Markdown 変換の確認" \
      --field-markdown "System.Description=@tools/markdown-fixture.md"

終了コードは、完全一致なら 0、書き換えがあれば 1。接続情報は `ado.py` と同じ環境変数
（`ADO_ORG_URL` / `ADO_PAT` / `ADO_PROJECT`）を使う。
"""
from __future__ import annotations

import argparse
import difflib
import importlib.util
import json
import pathlib
import re
import signal
import subprocess
import sys

try:  # `| head` で切られたときに追跡情報を吐かない。Windows に SIGPIPE はない
    signal.signal(signal.SIGPIPE, signal.SIG_DFL)
except (AttributeError, ValueError):
    pass

ROOT = pathlib.Path(__file__).resolve().parent.parent
ADO_PY = ROOT / ".claude/skills/azure-devops/scripts/ado.py"
FIXTURE = ROOT / "tools/markdown-fixture.md"

TAG = re.compile(r"<(/?)([a-zA-Z][\w-]*)")


def load_converter():
    spec = importlib.util.spec_from_file_location("ado", ADO_PY)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.md_to_html


def fetch(work_item_id, field):
    result = subprocess.run(
        [sys.executable, str(ADO_PY), "wit", "get", str(work_item_id), "--fields", field],
        capture_output=True, text=True)
    if result.returncode != 0:
        sys.exit(result.stderr.strip() or "ado.py wit get に失敗した")
    items = json.loads(result.stdout)
    if not items:
        sys.exit(f"作業アイテム {work_item_id} が見つからない")
    return items[0].get("fields", {}).get(field, "")


def tag_counts(markup):
    counts = {}
    for _, name in TAG.findall(markup):
        counts[name.lower()] = counts.get(name.lower(), 0) + 1
    return counts


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("id", help="書き込み済みの作業アイテム id")
    parser.add_argument("--field", default="System.Description",
                        help="比較するフィールドの参照名（既定: System.Description）")
    parser.add_argument("--source", default=str(FIXTURE),
                        help="書き込んだ Markdown のパス（既定: tools/markdown-fixture.md）")
    args = parser.parse_args()

    md_to_html = load_converter()
    sent = md_to_html(pathlib.Path(args.source).read_text(encoding="utf-8"))
    got = fetch(args.id, args.field)

    before, after = tag_counts(sent), tag_counts(got)
    print(f"送信 {len(sent)} 文字 / 取得 {len(got)} 文字\n")
    print("| タグ | 送信 | 取得 | 判定 |")
    print("| --- | --- | --- | --- |")
    for name in sorted(set(before) | set(after)):
        a, b = before.get(name, 0), after.get(name, 0)
        verdict = "OK" if a == b else ("落ちた" if b < a else "増えた")
        print(f"| {name} | {a} | {b} | {verdict} |")

    if sent == got:
        print("\n完全一致。サーバは何も書き換えていない。")
        return 0

    print("\nサーバが書き換えた箇所（- が送信、+ が取得）:")
    diff = [line for line in difflib.unified_diff(
        re.split(r"(?=<)", sent), re.split(r"(?=<)", got), "送信", "取得", lineterm="")
        if line[:1] in "+-" and line[:3] not in ("---", "+++")]
    print("\n".join(diff[:80]))
    if len(diff) > 80:
        print(f"… 他 {len(diff) - 80} 行")
    return 1


if __name__ == "__main__":
    sys.exit(main())
