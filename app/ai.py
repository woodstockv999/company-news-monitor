"""Haiku を使った意味的重複除去と記事要約。"""
from __future__ import annotations

import json
import logging
import re

import anthropic

from .sources import Item

logger = logging.getLogger(__name__)
MODEL = "claude-haiku-4-5-20251001"


def _client() -> anthropic.Anthropic:
    return anthropic.Anthropic()


def deduplicate(items: list[Item]) -> list[Item]:
    """同じ出来事を扱う重複記事を除去し、各トピックの代表1件を残す。

    API 呼び出し失敗時はフォールバックとして全件返す。
    """
    if len(items) <= 2:
        return items

    numbered = [{"i": i, "title": it.title} for i, it in enumerate(items)]
    prompt = (
        "以下のニュース記事タイトルを確認してください。\n"
        "同じ出来事・トピックを扱う記事がある場合、最も情報量の多い代表記事1件を残し、\n"
        "残すべき記事のインデックス番号だけをJSON配列で返してください。\n\n"
        f"{json.dumps(numbered, ensure_ascii=False)}\n\n"
        "出力はJSON配列のみ（例: [0, 2, 5]）。説明不要。"
    )

    try:
        resp = _client().messages.create(
            model=MODEL,
            max_tokens=256,
            messages=[{"role": "user", "content": prompt}],
        )
        text = resp.content[0].text.strip()
        m = re.search(r"\[[\d,\s]*\]", text)
        if not m:
            logger.warning("重複除去: JSONパース失敗 → フォールバック")
            return items
        keep = [i for i in json.loads(m.group()) if isinstance(i, int) and i < len(items)]
        if not keep:
            return items
        removed = len(items) - len(keep)
        if removed > 0:
            logger.info("重複除去: %d件 → %d件 (%d件削除)", len(items), len(keep), removed)
        return [items[i] for i in keep]
    except Exception as exc:
        logger.warning("重複除去スキップ (Haiku エラー): %s", exc)
        return items


def summarize(items: list[Item]) -> dict[str, str]:
    """各記事のタイトルから1〜2文の日本語要約を生成し {item.key: summary} で返す。

    API 呼び出し失敗時は空辞書を返す（要約なしで通常通りメール送信される）。
    """
    if not items:
        return {}

    titles = [it.title for it in items]
    prompt = (
        "以下のニュース記事タイトルそれぞれについて、"
        "記事の要点を1〜2文の日本語で簡潔に要約してください。\n\n"
        f"{json.dumps(titles, ensure_ascii=False)}\n\n"
        "同じ順番でJSON文字列配列として返してください。出力はJSON配列のみ。"
    )

    try:
        resp = _client().messages.create(
            model=MODEL,
            max_tokens=min(4096, len(items) * 150 + 64),
            messages=[{"role": "user", "content": prompt}],
        )
        text = resp.content[0].text.strip()
        m = re.search(r"\[.*\]", text, re.DOTALL)
        if not m:
            logger.warning("要約: JSONパース失敗 → スキップ")
            return {}
        raw = json.loads(m.group())
        result = {
            items[i].key: str(raw[i])
            for i in range(min(len(items), len(raw)))
            if raw[i]
        }
        logger.info("要約生成: %d件", len(result))
        return result
    except Exception as exc:
        logger.warning("要約スキップ (Haiku エラー): %s", exc)
        return {}
