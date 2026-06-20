"""companies.yml と環境変数から設定を読み込む。"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Optional

import yaml


@dataclass
class Source:
    """1つの監視対象（RSS フィード、もしくは HTML ニュース一覧ページ）。"""

    type: str
    url: str
    item_selector: Optional[str] = None  # type=html のとき記事リンクを選ぶ CSS セレクタ


@dataclass(eq=False)  # dict のキーとして使うため identity ハッシュにする
class Company:
    id: str
    name: str
    sources: list[Source] = field(default_factory=list)


@dataclass
class MailConfig:
    host: str
    port: int
    user: str
    password: str
    sender: str
    recipients: list[str]


def load_companies(path: str) -> list[Company]:
    """companies.yml を読み込んで Company のリストを返す。"""
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    companies: list[Company] = []
    for raw in data.get("companies", []):
        sources = []
        for s in raw.get("sources", []):
            sources.append(
                Source(
                    type=s["type"],
                    url=s["url"],
                    item_selector=s.get("item_selector"),
                )
            )
        companies.append(
            Company(id=raw["id"], name=raw.get("name", raw["id"]), sources=sources)
        )
    return companies


def load_mail_config() -> MailConfig:
    """環境変数（GitHub Secrets）からメール設定を読み込む。"""
    user = os.environ.get("SMTP_USER", "")
    recipients = [
        r.strip() for r in os.environ.get("MAIL_TO", "").split(",") if r.strip()
    ]
    return MailConfig(
        host=os.environ.get("SMTP_HOST", "smtp.gmail.com"),
        port=int(os.environ.get("SMTP_PORT", "587")),
        user=user,
        password=os.environ.get("SMTP_PASS", ""),
        sender=os.environ.get("MAIL_FROM") or user,
        recipients=recipients,
    )
