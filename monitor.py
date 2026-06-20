#!/usr/bin/env python3
"""企業ニュースを監視し、新着があればメール通知する。

GitHub Actions（self-hosted runner）から日次で実行される想定。
state.json に既読履歴を保存し、差分のみを通知する。
"""
from __future__ import annotations

import argparse
import logging
import sys

from app.config import load_companies, load_mail_config
from app.notifier import render_text, send_email
from app.sources import fetch_source
from app.state import load_state, save_state

# 1社あたりの既読履歴の上限。state.json が無限に肥大化するのを防ぐ。
MAX_SEEN = 1000

logger = logging.getLogger("monitor")


def run(companies_path: str, state_path: str, dry_run: bool = False) -> int:
    companies = load_companies(companies_path)
    state = load_state(state_path)
    cstate = state.setdefault("companies", {})

    new_by_company: dict = {}

    for company in companies:
        entry = cstate.setdefault(company.id, {"seen": [], "initialized": False})
        seen = set(entry["seen"])

        # 全 source から項目を集めて、key で重複排除（順序は維持）
        uniq: dict = {}
        for source in company.sources:
            try:
                for item in fetch_source(source):
                    uniq.setdefault(item.key, item)
            except Exception as exc:  # 1つの source 失敗で全体を止めない
                logger.error("取得失敗 %s (%s): %s", company.id, source.url, exc)

        # 初回はベースライン化のみ（登録直後に過去記事を大量通知しない）
        if not entry["initialized"]:
            entry["seen"] = list(uniq.keys())[-MAX_SEEN:]
            entry["initialized"] = True
            logger.info("%s: ベースライン設定 (%d件)", company.id, len(uniq))
            continue

        new_items = [it for key, it in uniq.items() if key not in seen]
        if new_items:
            new_by_company[company] = new_items
            entry["seen"].extend(it.key for it in new_items)
            entry["seen"] = entry["seen"][-MAX_SEEN:]
            logger.info("%s: 新着 %d件", company.id, len(new_items))
        else:
            logger.info("%s: 新着なし", company.id)

    # config から消えた企業の履歴は state からも削除して整合させる
    valid_ids = {c.id for c in companies}
    for stale_id in [cid for cid in cstate if cid not in valid_ids]:
        del cstate[stale_id]
        logger.info("%s: config から削除されたため履歴を破棄", stale_id)

    total = sum(len(v) for v in new_by_company.values())
    if new_by_company:
        if dry_run:
            print(render_text(new_by_company))
            logger.info("[dry-run] メール送信はスキップしました")
        else:
            send_email(new_by_company, load_mail_config())
    else:
        logger.info("新着はありませんでした。メールは送信しません。")

    save_state(state_path, state)
    return total


def main() -> None:
    parser = argparse.ArgumentParser(description="企業ニュース監視")
    parser.add_argument("--companies", default="companies.yml", help="企業設定ファイル")
    parser.add_argument("--state", default="state.json", help="既読履歴ファイル")
    parser.add_argument(
        "--dry-run", action="store_true", help="メールを送らず結果を標準出力に表示"
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    try:
        run(args.companies, args.state, dry_run=args.dry_run)
    except Exception as exc:
        logger.exception("致命的エラー: %s", exc)
        sys.exit(1)


if __name__ == "__main__":
    main()
