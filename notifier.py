"""
QQ邮箱日报 —— 分"集成电路相关"和"其他通知"两类汇总
"""
import smtplib
from datetime import datetime, timedelta, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from config import SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS, RECIPIENT

CST = timezone(timedelta(hours=8))


def send_daily_report(notices: list[dict]) -> bool:
    """
    发送日报邮件，分两类：
    1. 集成电路相关
    2. 其他通知
    """
    if not notices:
        print("  没有通知，跳过邮件发送")
        return True

    relevant = [n for n in notices if n.get("relevant")]
    others = [n for n in notices if not n.get("relevant")]

    now = datetime.now(CST)
    date_str = now.strftime("%m月%d日")
    total = len(notices)

    subject = f"【保研日报】{date_str} · 相关 {len(relevant)} 条 / 共 {total} 条"

    text_body = _build_text(relevant, others, date_str, total)
    html_body = _build_html(relevant, others, date_str, total)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = SMTP_USER
    msg["To"] = RECIPIENT
    msg.attach(MIMEText(text_body, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as server:
            server.login(SMTP_USER, SMTP_PASS)
            server.sendmail(SMTP_USER, [RECIPIENT], msg.as_string())
        print(f"  邮件已发送: {subject}")
        return True
    except Exception as e:
        print(f"  [ERROR] 邮件发送失败: {e}")
        return False


# ── 纯文本 ────────────────────────────────────────────

def _build_text(relevant: list, others: list, date_str: str, total: int) -> str:
    parts = [
        f"保研通知日报 · {date_str}",
        f"共 {total} 条新通知，其中集成电路相关 {len(relevant)} 条",
        "=" * 40,
    ]

    if relevant:
        parts.append(f"\n{'─' * 30}")
        parts.append(f" 集成电路相关 ({len(relevant)} 条)")
        parts.append(f"{'─' * 30}")
        parts.extend(_format_list(relevant))

    if others:
        parts.append(f"\n{'─' * 30}")
        parts.append(f" 其他通知 ({len(others)} 条)")
        parts.append(f"{'─' * 30}")
        parts.extend(_format_list(others))

    return "\n".join(parts)


def _format_list(notices: list) -> list:
    lines = []
    for i, n in enumerate(notices, 1):
        title = n.get("title", "无标题")
        school = n.get("school", "")
        college = n.get("college", "")
        recruit_type = n.get("recruit_type", "")
        end_time = n.get("end_time", "")
        reason = n.get("reason", "")
        summary = _summarize(n.get("full_text", ""))

        lines.append(f"\n{i}. [{recruit_type}] {school} {college}")
        lines.append(f"   {title}")
        if summary:
            lines.append(f"   摘要：{summary}")
        if end_time:
            lines.append(f"   ⏰ 截止：{end_time}")
        if reason:
            lines.append(f"   📌 {reason}")
        lines.append(f"   🔗 {n['url']}")
    return lines


# ── HTML ──────────────────────────────────────────────

def _build_html(relevant: list, others: list, date_str: str, total: int) -> str:
    sections = ""

    if relevant:
        sections += f"""
        <div style="margin-bottom:20px;">
          <div style="background:#e8f5e9;padding:10px 14px;border-radius:6px;margin-bottom:12px;
                      font-weight:700;color:#2e7d32;font-size:15px;">
            集成电路相关 · {len(relevant)} 条
          </div>
          {''.join(_html_items(relevant, border_color='#4caf50'))}
        </div>"""

    if others:
        sections += f"""
        <div style="margin-bottom:20px;">
          <div style="background:#f5f5f5;padding:10px 14px;border-radius:6px;margin-bottom:12px;
                      font-weight:700;color:#666;font-size:15px;">
            其他通知 · {len(others)} 条
          </div>
          {''.join(_html_items(others, border_color='#ccc'))}
        </div>"""

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"></head>
<body style="font-family:'Microsoft YaHei',Arial,sans-serif;max-width:680px;margin:0 auto;padding:16px;">
  <div style="background:#214ab3;color:#fff;padding:18px;border-radius:10px 10px 0 0;">
    <h2 style="margin:0;font-size:18px;">保研通知日报</h2>
    <div style="font-size:12px;opacity:0.85;margin-top:4px;">
      {date_str} · 共 {total} 条新通知
    </div>
  </div>
  <div style="background:#fff;padding:20px;border:1px solid #e0e0e0;border-top:0;border-radius:0 0 10px 10px;">
    {sections}
  </div>
  <div style="text-align:center;font-size:11px;color:#aaa;margin-top:12px;">
    自动监控 · 每日 20:00 · 数据来源 <a href="https://www.baoyantongzhi.com/notice" style="color:#aaa;">保研通知网</a>
  </div>
</body></html>"""


def _html_items(notices: list, border_color: str) -> list:
    items = []
    for i, n in enumerate(notices, 1):
        title = n.get("title", "无标题")
        school = n.get("school", "")
        college = n.get("college", "")
        recruit_type = n.get("recruit_type", "")
        end_time = n.get("end_time", "")
        reason = n.get("reason", "")
        summary = _summarize(n.get("full_text", ""))

        item = f"""
        <div style="margin-bottom:20px;border-left:3px solid {border_color};padding-left:12px;">
          <div style="font-size:13px;color:#888;margin-bottom:4px;">
            [{recruit_type}] {school} · {college}
          </div>
          <div style="font-size:15px;color:#333;margin-bottom:8px;font-weight:600;">
            {i}. {title}
          </div>"""
        if summary:
            item += f"""
          <div style="font-size:13px;color:#555;margin-bottom:4px;line-height:1.6;">
            {summary}
          </div>"""
        if end_time:
            item += f"""
          <div style="font-size:14px;color:#e67e22;margin-bottom:4px;font-weight:600;">
            ⏰ 截止：{end_time}
          </div>"""
        if reason:
            item += f"""
          <div style="font-size:12px;color:#999;margin-bottom:4px;">
            📌 {reason}
          </div>"""
        item += f"""
          <div style="font-size:13px;">
            🔗 <a href="{n['url']}" style="color:#214ab3;">查看详情</a>
          </div>
        </div>"""
        items.append(item)
    return items


def _summarize(text: str, max_len: int = 150) -> str:
    if not text:
        return ""
    text = text.replace("\r", "").strip()
    lines = [l.strip() for l in text.split("\n") if l.strip() and len(l.strip()) > 20]
    for line in lines:
        if len(line) > max_len:
            return line[:max_len] + "…"
        return line
    return ""
