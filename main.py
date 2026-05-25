"""
保研通知网 · 集成电路专业监控系统
每天定时抓取 → DeepSeek 语义分析 → QQ邮箱日报（相关+无关）
"""
import asyncio
import json
import os
import sys
from datetime import datetime, timedelta, timezone

# 测试邮件模式：跳过重依赖
if "--test-email" in sys.argv:
    from notifier import send_daily_report
    test_notices = [{
        "id": 99999,
        "title": "【示例】北京大学集成电路学院2026年优秀大学生夏令营报名通知",
        "school": "北京大学",
        "college": "集成电路学院",
        "recruit_type": "夏令营",
        "end_time": "2026-06-30 23:59:59",
        "url": "https://www.baoyantongzhi.com/notice/detail/99999",
        "reason": "集成电路学院夏令营，直接相关",
        "full_text": "北京大学集成电路学院将于2026年7月10日-15日举办优秀大学生夏令营，面向全国高校招收大三优秀本科生。招生方向包括：集成电路设计、微电子学与固体电子学、半导体器件与工艺、EDA工具等。",
        "relevant": True,
    }, {
        "id": 99998,
        "title": "【示例】清华大学微电子与纳电子学系2026年夏令营通知",
        "school": "清华大学",
        "college": "微电子与纳电子学系",
        "recruit_type": "夏令营",
        "end_time": "2026-07-05 23:59:59",
        "url": "https://www.baoyantongzhi.com/notice/detail/99998",
        "reason": "微电子与纳电子学系，集成电路相关方向",
        "full_text": "清华大学微电子与纳电子学系拟于2026年7月中旬举办全国优秀大学生夏令营。招收方向：集成电路设计与设计自动化、微纳器件与集成、射频与混合信号集成电路等。",
        "relevant": True,
    }, {
        "id": 99997,
        "title": "【示例】北京师范大学文理学院2026年优秀大学生夏令营报名通知",
        "school": "北京师范大学",
        "college": "文理学院",
        "recruit_type": "夏令营",
        "end_time": "2026-06-06 23:59:59",
        "url": "https://www.baoyantongzhi.com/notice/detail/99997",
        "reason": "文理学院涵盖中文、历史、数学等基础学科，与集成电路无关",
        "full_text": "北京师范大学文理学院下设中文系、历史系、哲学系等13个文理基础学科专业系，聚焦文理基础学科。",
        "relevant": False,
    }]
    print("发送测试邮件...")
    send_daily_report(test_notices)
    print("测试邮件发送完成！")
    sys.exit(0)

from config import SEEN_FILE, MONITOR_END_DATE
from scraper import fetch_notice_list, fetch_detail_batch, enrich_notice_with_list_data
from analyzer import analyze
from notifier import send_daily_report

CST = timezone(timedelta(hours=8))


def load_seen() -> set[int]:
    if not os.path.exists(SEEN_FILE):
        return set()
    with open(SEEN_FILE, encoding="utf-8") as f:
        data = json.load(f)
    return set(data.get("ids", []))


def save_seen(ids: set[int]):
    with open(SEEN_FILE, "w", encoding="utf-8") as f:
        json.dump({
            "ids": sorted(ids),
            "last_run": datetime.now(timezone.utc).isoformat(),
        }, f, ensure_ascii=False, indent=2)


def should_continue() -> bool:
    today = datetime.now(timezone.utc).date()
    try:
        end = datetime.strptime(MONITOR_END_DATE, "%Y-%m-%d").date()
        return today <= end
    except ValueError:
        return True


async def main():
    now_str = datetime.now(CST).strftime("%Y-%m-%d %H:%M:%S")
    print("=" * 60)
    print(f"保研通知日报 · {now_str} (CST)")
    print("=" * 60)

    if not should_continue():
        print("监控周期已结束（超过9月30日），退出。")
        return

    # ── 1. 抓取通知列表 ──
    print("\n[1/4] 抓取通知列表...")
    try:
        notices = await fetch_notice_list()
        print(f"  获取到 {len(notices)} 条最近通知")
    except Exception as e:
        print(f"  [FATAL] 列表抓取失败: {e}")
        sys.exit(1)

    if not notices:
        print("  没有找到任何通知，发送心跳确认邮件。")
        from notifier import send_heartbeat
        send_heartbeat()
        return

    # ── 2. 去重 ──
    seen_ids = load_seen()
    new_notices = [n for n in notices if n.get("id") not in seen_ids]
    print(f"\n[2/4] 去重: 已记录 {len(seen_ids)} 条, 今日新增 {len(new_notices)} 条")

    if not new_notices:
        print("  今日没有新通知，发送心跳确认邮件。")
        from notifier import send_heartbeat
        send_heartbeat()
        all_ids = {n["id"] for n in notices if n.get("id")}
        save_seen(all_ids | seen_ids)
        return

    # ── 3. 抓取详情 + DeepSeek 分析 ──
    print(f"\n[3/4] 抓取 {len(new_notices)} 条详情并分析...")
    new_ids = [n["id"] for n in new_notices if n.get("id")]
    detail_map = await fetch_detail_batch(new_ids, concurrency=5)

    list_data_map = {n["id"]: n for n in new_notices if n.get("id")}
    details = []
    for nid, detail in detail_map.items():
        meta = list_data_map.get(nid, {})
        enriched = enrich_notice_with_list_data(meta)
        enriched["full_text"] = detail.get("full_text", "")
        enriched["url"] = detail.get("url", "")
        details.append(enriched)

    print(f"  成功获取 {len(details)} 条详情，DeepSeek 分析中...")
    results = analyze(details)

    # 合并分析结果
    result_map = {r["id"]: r for r in results}
    for d in details:
        r = result_map.get(d["id"])
        d["relevant"] = r.get("relevant", False) if r else False
        d["reason"] = r.get("reason", "") if r else ""

    relevant_count = sum(1 for d in details if d.get("relevant"))
    print(f"  分析完成: 集成电路相关 {relevant_count} 条, 无关 {len(details) - relevant_count} 条")

    # ── 4. 发送日报 ──
    print(f"\n[4/4] 发送日报邮件...")
    send_daily_report(details)

    # ── 5. 更新 seen.json ──
    all_ids = {n["id"] for n in notices if n.get("id")}
    save_seen(all_ids | seen_ids)
    print(f"\n完成。seen.json 已更新。")


if __name__ == "__main__":
    asyncio.run(main())
