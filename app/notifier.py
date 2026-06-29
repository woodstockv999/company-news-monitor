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


def render_text(
    new_by_company: dict[Company, list[Item]],
    summaries: dict[str, str] | None = None,
) -> str:
    s = summaries or {}
    total = sum(len(v) for v in new_by_company.values())
    lines = [f"企業ニュース監視: {total}件の新着 ({len(new_by_company)}社)", ""]
    for company, items in new_by_company.items():
        lines.append(f"■ {company.name}  ({len(items)}件)")
        for it in items:
            pub = f"  ({it.published})" if it.published else ""
            lines.append(f"  ・{it.title}{pub}")
            if it.key in s:
                lines.append(f"    {s[it.key]}")
            lines.append(f"    {it.url}")
        lines.append("")
    return "\n".join(lines)


def render_html(
    new_by_company: dict[Company, list[Item]],
    summaries: dict[str, str] | None = None,
) -> str:
    s = summaries or {}
    parts = [
        "<html><body style='font-family:sans-serif;line-height:1.7;max-width:680px;margin:0 auto;padding:16px'>",
        f"<h2 style='color:#1a1a2e'>{html.escape(_subject(new_by_company))}</h2>",
    ]
    for company, items in new_by_company.items():
        parts.append(
            f"<h3 style='color:#16213e;border-bottom:2px solid #e0e0e0;padding-bottom:4px'>"
            f"{html.escape(company.name)} <small style='color:#888;font-size:0.75em'>({len(items)}件)</small></h3>"
            f"<ul style='list-style:none;padding:0'>"
        )
        for it in items:
            pub = (
                f" <span style='color:#999;font-size:0.8em'>({html.escape(it.published)})</span>"
                if it.published else ""
            )
            url = html.escape(it.url)
            title = html.escape(it.title)
            summary_html = (
                f"<p style='margin:4px 0 8px;color:#444;font-size:0.9em'>{html.escape(s[it.key])}</p>"
                if it.key in s else ""
            )
            parts.append(
                f"<li style='margin-bottom:16px;padding:12px;background:#f9f9f9;border-radius:6px'>"
                f"<a href='{url}' style='font-weight:bold;color:#0066cc;text-decoration:none'>{title}</a>{pub}"
                f"{summary_html}"
                f"</li>"
            )
        parts.append("</ul>")
    parts.append("</body></html>")
    return "".join(parts)


def send_email(
    new_by_company: dict[Company, list[Item]],
    mail: MailConfig,
    summaries: dict[str, str] | None = None,
) -> None:
    if not mail.recipients:
        raise RuntimeError("MAIL_TO（送信先）が設定されていません。")
    if not mail.user or not mail.password:
        raise RuntimeError("SMTP_USER / SMTP_PASS が設定されていません。")

    msg = MIMEMultipart("alternative")
    msg["Subject"] = str(Header(_subject(new_by_company), "utf-8"))
    msg["From"] = mail.sender
    msg["To"] = ", ".join(mail.recipients)
    msg.attach(MIMEText(render_text(new_by_company, summaries), "plain", "utf-8"))
    msg.attach(MIMEText(render_html(new_by_company, summaries), "html", "utf-8"))

    with smtplib.SMTP(mail.host, mail.port, timeout=30) as server:
        server.starttls()
        server.login(mail.user, mail.password)
        server.sendmail(mail.sender, mail.recipients, msg.as_string())
    logger.info("メールを送信しました: %s", ", ".join(mail.recipients))
