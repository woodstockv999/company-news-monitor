"""新着ニュースをメールで通知する。"""
from __future__ import annotations

import html
import logging
import smtplib
from email.header import Header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from .config import Company, MailConfig
from .sources import Item

logger = logging.getLogger(__name__)


def _subject(new_by_company: dict[Company, list[Item]]) -> str:
    total = sum(len(v) for v in new_by_company.values())
    return f"[ニュース監視] {total}件の新着 ({len(new_by_company)}社)"


def render_text(new_by_company: dict[Company, list[Item]]) -> str:
    total = sum(len(v) for v in new_by_company.values())
    lines = [f"企業ニュース監視: {total}件の新着 ({len(new_by_company)}社)", ""]
    for company, items in new_by_company.items():
        lines.append(f"■ {company.name}")
        for it in items:
            pub = f"  ({it.published})" if it.published else ""
            lines.append(f"  - {it.title}{pub}")
            lines.append(f"    {it.url}")
        lines.append("")
    return "\n".join(lines)


def render_html(new_by_company: dict[Company, list[Item]]) -> str:
    parts = ["<html><body style='font-family:sans-serif;line-height:1.6'>"]
    parts.append(f"<h2>{html.escape(_subject(new_by_company))}</h2>")
    for company, items in new_by_company.items():
        parts.append(f"<h3>{html.escape(company.name)}</h3><ul>")
        for it in items:
            pub = f" <span style='color:#888'>({html.escape(it.published)})</span>" if it.published else ""
            url = html.escape(it.url)
            title = html.escape(it.title)
            parts.append(f"<li><a href='{url}'>{title}</a>{pub}</li>")
        parts.append("</ul>")
    parts.append("</body></html>")
    return "".join(parts)


def send_email(new_by_company: dict[Company, list[Item]], mail: MailConfig) -> None:
    if not mail.recipients:
        raise RuntimeError("MAIL_TO（送信先）が設定されていません。")
    if not mail.user or not mail.password:
        raise RuntimeError("SMTP_USER / SMTP_PASS が設定されていません。")

    msg = MIMEMultipart("alternative")
    msg["Subject"] = str(Header(_subject(new_by_company), "utf-8"))
    msg["From"] = mail.sender
    msg["To"] = ", ".join(mail.recipients)
    msg.attach(MIMEText(render_text(new_by_company), "plain", "utf-8"))
    msg.attach(MIMEText(render_html(new_by_company), "html", "utf-8"))

    with smtplib.SMTP(mail.host, mail.port, timeout=30) as server:
        server.starttls()
        server.login(mail.user, mail.password)
        server.sendmail(mail.sender, mail.recipients, msg.as_string())
    logger.info("メールを送信しました: %s", ", ".join(mail.recipients))
