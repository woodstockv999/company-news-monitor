#!/usr/bin/env python3
"""企業の登録・削除・一覧表示を行う簡易CLI。

例:
  python manage.py list
  python manage.py add  --id sony --name "ソニーグループ" --rss https://example.com/feed.xml
  python manage.py add  --id foo  --name "Foo社" --html https://example.com/news/ --selector "a.news-link"
  python manage.py remove --id sony

companies.yml を直接編集しても構いません（こちらは入力補助）。
"""
from __future__ import annotations

import argparse
import sys

import yaml

DEFAULT_PATH = "companies.yml"


def _load(path: str) -> dict:
    try:
        with open(path, encoding="utf-8") as f:
            return yaml.safe_load(f) or {"companies": []}
    except FileNotFoundError:
        return {"companies": []}


def _save(path: str, data: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False)


def cmd_list(args: argparse.Namespace) -> None:
    data = _load(args.file)
    companies = data.get("companies", [])
    if not companies:
        print("登録されている企業はありません。")
        return
    for c in companies:
        print(f"- {c['id']}: {c.get('name', '')}")
        for s in c.get("sources", []):
            extra = f"  selector={s['item_selector']}" if s.get("item_selector") else ""
            print(f"    [{s['type']}] {s['url']}{extra}")


def cmd_add(args: argparse.Namespace) -> None:
    if not args.rss and not args.html:
        sys.exit("--rss または --html のどちらかを指定してください。")

    data = _load(args.file)
    companies = data.setdefault("companies", [])

    if any(c["id"] == args.id for c in companies):
        sys.exit(f"id '{args.id}' は既に存在します。先に remove するか別のidを使ってください。")

    sources = []
    if args.rss:
        sources.append({"type": "rss", "url": args.rss})
    if args.html:
        src = {"type": "html", "url": args.html}
        if args.selector:
            src["item_selector"] = args.selector
        sources.append(src)

    companies.append({"id": args.id, "name": args.name or args.id, "sources": sources})
    _save(args.file, data)
    print(f"追加しました: {args.id} ({args.name or args.id})")


def cmd_remove(args: argparse.Namespace) -> None:
    data = _load(args.file)
    companies = data.get("companies", [])
    new = [c for c in companies if c["id"] != args.id]
    if len(new) == len(companies):
        sys.exit(f"id '{args.id}' が見つかりません。")
    data["companies"] = new
    _save(args.file, data)
    print(f"削除しました: {args.id}（state.json の履歴は次回実行時に自動で整理されます）")


def main() -> None:
    parser = argparse.ArgumentParser(description="企業の登録・削除")
    parser.add_argument("--file", default=DEFAULT_PATH, help="companies.yml のパス")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list", help="一覧表示").set_defaults(func=cmd_list)

    p_add = sub.add_parser("add", help="企業を追加")
    p_add.add_argument("--id", required=True, help="一意なID（半角英数推奨）")
    p_add.add_argument("--name", help="表示名")
    p_add.add_argument("--rss", help="RSS/Atom フィードのURL")
    p_add.add_argument("--html", help="ニュース一覧ページのURL")
    p_add.add_argument("--selector", help="type=html のとき記事リンクのCSSセレクタ")
    p_add.set_defaults(func=cmd_add)

    p_rm = sub.add_parser("remove", help="企業を削除")
    p_rm.add_argument("--id", required=True)
    p_rm.set_defaults(func=cmd_remove)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
