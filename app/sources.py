"""RSS / HTML からニュース項目を取得する。"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from urllib.parse import urljoin

import feedparser
import requests
from bs4 import BeautifulSoup

from .config import Source

# 一部サイトはデフォルトのUAを弾くため、ブラウザ相当のUAを使う
USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
TIMEOUT = 30


@dataclass
class Item:
    """ニュース1件。key は重複判定に使う一意なキー（記事URLなど）。"""

    key: str
    title: str
    url: str
    published: str = ""
    published_dt: datetime | None = field(default=None, compare=False)


def fetch_source(source: Source) -> list[Item]:
    if source.type == "rss":
        return _fetch_rss(source)
    if source.type == "html":
        return _fetch_html(source)
    raise ValueError(f"未知の source type: {source.type}")


def _fetch_rss(source: Source) -> list[Item]:
    feed = feedparser.parse(source.url, agent=USER_AGENT)
    items: list[Item] = []
    for entry in feed.entries:
        url = entry.get("link", "")
        key = entry.get("id") or url or entry.get("title", "")
        title = (entry.get("title") or "(no title)").strip()
        published = entry.get("published", entry.get("updated", ""))
        if not key:
            continue
        parsed_tuple = entry.get("published_parsed") or entry.get("updated_parsed")
        published_dt: datetime | None = None
        if parsed_tuple:
            try:
                published_dt = datetime.fromtimestamp(
                    time.mktime(parsed_tuple), tz=timezone.utc
                )
            except (OverflowError, OSError):
                pass
        items.append(
            Item(key=key.strip(), title=title, url=url, published=published, published_dt=published_dt)
        )
    return items


def _fetch_html(source: Source) -> list[Item]:
    resp = requests.get(
        source.url, headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT
    )
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    selector = source.item_selector or "a"
    items: list[Item] = []
    seen: set[str] = set()
    for el in soup.select(selector):
        href = el.get("href")
        if not href:
            continue
        url = urljoin(source.url, href)
        if url in seen:
            continue
        seen.add(url)
        title = el.get_text(strip=True) or url
        items.append(Item(key=url, title=title, url=url))
    return items
