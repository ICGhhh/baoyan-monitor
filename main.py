"""
保研通知网 · 集成电路专业监控系统
每天定时抓取 → DeepSeek 语义分析 → QQ邮箱通知
"""
import asyncio
import json
import os
import sys
from datetime import datetime, timezone, timedelta

# 测试邮件模式：先处理，避免加载 playwright 等重依赖
if "--test-email" in sys.argv:
    from notifier import send
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
    }, {
        "id": 99998,
        "title": "【示例】清华大学微电子与纳电子学系2026年夏令营通知",
        "school": "清华大学",
        "college": "微电子与纳电子学系",
        "recruit_type": "夏令营",
        "end_time": "2026-07-05 23:59:59",
        "url": "https://www.baoyantongzhi.com/notice/detail/99998",
        "reason": "微电子与纳电子学系，属于集成电路相关方向",
        "full_text": "清华大学微电子与纳电子学系拟于2026年7月中旬举办全国优秀大学生夏令营。招收方向：集成电路设计与设计自动化、微纳器件与集成、射频与混合信号集成电路等。",
    }]
    print("发送测试邮件...")
    send(test_notices)
    print("测试邮件发送完成，请检查邮箱。")
    sys.exit(0)

from config import SEEN_FILE, MONITOR_END_DATE
from scraper import fetch_notice_list, fetch_detail_batch, enrich_notice_with_list_data
from analyzer import analyze

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
    print(f"保研通知监控 · {now_str} (CST)")
    print("=" * 60)

    if not should_continue():
        print("监控周期已结束（超过9月30日），退出。")
        return

    # ── 1. 抓取通知列表 ──
    print("\n[1/5] 抓取通知列表...")
    try:
        notices = await fetch_notice_list()
        print(f"  获取到 {len(notices)} 条最近通知")
    except Exception as e:
        print(f"  [FATAL] 列表抓取失败: {e}")
        sys.exit(1)

    if not notices:
        print("  没有找到任何通知，退出。")
        return

    # ── 2. 去重 ──
    seen_ids = load_seen()
    is_first_run = len(seen_ids) == 0
    new_notices = [n for n in notices if n.get("id") not in seen_ids]
    print(f"\n[2/5] 去重: 已记录 {len(seen_ids)} 条, 新增 {len(new_notices)} 条")

    if not new_notices:
        print("  没有新通知，退出。")
        all_ids = {n["id"] for n in notices if n.get("id")}
        save_seen(all_ids | seen_ids)
        return

    # ── 3. 抓取详情页 ──
    print(f"\n[3/5] 抓取 {len(new_notices)} 条详情页（并发）...")
    new_ids = [n["id"] for n in new_notices if n.get("id")]
    detail_map = await fetch_detail_batch(new_ids, concurrency=5)

    # 将列表元数据 + 详情文本合并
    list_data_map = {n["id"]: n for n in new_notices if n.get("id")}
    details = []
    for nid, detail in detail_map.items():
        meta = list_data_map.get(nid, {})
        enriched = enrich_notice_with_list_data(meta)
        enriched["full_text"] = detail.get("full_text", "")
        enriched["url"] = detail.get("url", "")
        details.append(enriched)

    print(f"  成功获取 {len(details)} 条详情")

    if not details:
        all_ids = {n["id"] for n in notices if n.get("id")}
        save_seen(all_ids | seen_ids)
        return

    # ── 4. DeepSeek 语义分析 ──
    print(f"\n[4/5] DeepSeek 语义分析...")
    results = analyze(details)

    relevant = [r for r in results if r.get("relevant")]
    print(f"  分析完成: 共 {len(results)} 条, 集成电路相关 {len(relevant)} 条")

    for r in relevant:
        print(f"    ✅ [{r.get('id')}] {r.get('reason', '')}")

    # ── 5. 发送通知 ──
    print(f"\n[5/5] 发送通知...")

    result_map = {r["id"]: r for r in results}
    notices_to_send = []
    for d in details:
        r = result_map.get(d["id"])
        if r and r.get("relevant"):
            d["reason"] = r.get("reason", "")
            notices_to_send.append(d)

    if is_first_run:
        print(f"  首次运行，发现 {len(notices_to_send)} 条相关通知，仅保存状态不发送。")
    elif notices_to_send:
        send(notices_to_send)
    else:
        print("  没有新增相关通知，不发送邮件。")

    # ── 6. 更新 seen.json ──
    all_ids = {n["id"] for n in notices if n.get("id")}
    save_seen(all_ids | seen_ids)
    print(f"\n完成。seen.json 已更新 ({len(all_ids | seen_ids)} 条记录)。")


if __name__ == "__main__":
    asyncio.run(main())
