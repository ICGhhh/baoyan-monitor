"""
QQ邮箱通知 —— SMTP 发送每日集成电路相关通知汇总
"""
import smtplib
from datetime import datetime, timedelta, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from config import SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS, RECIPIENT

CST = timezone(timedelta(hours=8))


def send(notices: list[dict]) -> bool:
    """
    发送通知邮件。
    notices: 每条包含 title, school, college, recruit_type, end_time, url, reason, full_text
    """
    if not notices:
        print("  没有新通知，跳过邮件发送")
        return True

    now = datetime.now(CST)
    date_str = now.strftime("%m月%d日")
    subject = f"【保研通知】{date_str} 新增 {len(notices)} 条集成电路相关通知"

    text_body = _build_text(notices)
    html_body = _build_html(notices, date_str)

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


def _build_text(notices: list[dict]) -> str:
    parts = []
    for i, n in enumerate(notices, 1):
        title = n.get("title", "无标题")
        school = n.get("school", "")
        college = n.get("college", "")
        recruit_type = n.get("recruit_type", "")
        end_time = n.get("end_time", "")
        reason = n.get("reason", "")
        summary = _summarize(n.get("full_text", ""))

        line = f"{i}. [{recruit_type}] {school} {college} — {title}"
        if summary:
            line += f"\n   摘要：{summary}"
        if end_time:
            line += f"\n   ⏰ 截止日期：{end_time}"
        if reason:
            line += f"\n   📌 {reason}"
        line += f"\n   🔗 {n['url']}\n"
        parts.append(line)

    return "\n".join(parts)


def _build_html(notices: list[dict], date_str: str) -> str:
    items_html = []
    for i, n in enumerate(notices, 1):
        title = n.get("title", "无标题")
        school = n.get("school", "")
        college = n.get("college", "")
        recruit_type = n.get("recruit_type", "")
        end_time = n.get("end_time", "")
        reason = n.get("reason", "")
        summary = _summarize(n.get("full_text", ""))

        item = f"""
        <div style="margin-bottom:24px;border-left:3px solid #214ab3;padding-left:12px;">
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
            ⏰ 截止日期：{end_time}
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
        items_html.append(item)

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"></head>
<body style="font-family:'Microsoft YaHei',Arial,sans-serif;max-width:640px;margin:0 auto;padding:16px;">
  <div style="background:#214ab3;color:#fff;padding:18px;border-radius:8px 8px 0 0;">
    <h2 style="margin:0;font-size:18px;">
      保研通知 · 集成电路专业监控
    </h2>
    <div style="font-size:12px;opacity:0.85;margin-top:4px;">
      {date_str} · 新增 {len(notices)} 条相关通知
    </div>
  </div>
  <div style="background:#fff;padding:20px;border:1px solid #e0e0e0;border-top:0;border-radius:0 0 8px 8px;">
    {''.join(items_html)}
  </div>
  <div style="text-align:center;font-size:11px;color:#aaa;margin-top:12px;">
    自动监控系统 · 每日 20:00 · 数据来源 <a href="https://www.baoyantongzhi.com/notice" style="color:#aaa;">保研通知网</a>
  </div>
</body></html>"""


def _summarize(text: str, max_len: int = 150) -> str:
    """从正文提取摘要"""
    if not text:
        return ""
    text = text.replace("\r", "").strip()
    lines = [l.strip() for l in text.split("\n") if l.strip() and len(l.strip()) > 20]
    for line in lines:
        if len(line) > max_len:
            return line[:max_len] + "…"
        return line
    return ""
