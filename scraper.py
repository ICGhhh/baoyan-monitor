"""
保研通知网爬虫 —— Playwright 浏览器内调用后端 API
"""
import asyncio
import re
from datetime import datetime, timedelta, timezone

from playwright.async_api import async_playwright

from config import API_BASE, NOTICE_YEAR, FETCH_SIZE, LOOKBACK_DAYS

FRONTEND_URL = "https://www.baoyantongzhi.com"
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/125.0.0.0 Safari/537.36"
)
CST = timezone(timedelta(hours=8))


async def _get_page():
    """创建已访问主站的浏览器页面（建立 origin 以便调用后端 API）"""
    p = await async_playwright().start()
    browser = await p.chromium.launch(headless=True)
    ctx = await browser.new_context(user_agent=UA, locale="zh-CN")
    page = await ctx.new_page()
    await page.goto(f"{FRONTEND_URL}/notice", wait_until="networkidle", timeout=60000)
    await asyncio.sleep(1)
    return p, browser, page


async def fetch_notice_list() -> list[dict]:
    """在浏览器内调用后端列表 API，返回通知列表"""
    p, browser, page = await _get_page()

    api_url = (
        f"{API_BASE}/backgd/notice/show/list"
        f"?current=1&size={FETCH_SIZE}&year={NOTICE_YEAR}&orderBy=publishTime"
    )
    result = await page.evaluate(
        """async (url) => {
            const resp = await fetch(url);
            return await resp.json();
        }""",
        api_url,
    )

    await browser.close()
    await p.stop()

    if not result or result.get("code") != 200:
        print(f"  [ERROR] API 返回异常: {result}")
        return []

    records = result["data"]["records"]

    # 按发布时间过滤
    cutoff = datetime.now(CST) - timedelta(days=LOOKBACK_DAYS)
    filtered = []
    for n in records:
        pub_time = _parse_publish_time(n)
        if pub_time and pub_time >= cutoff:
            n["_pub_dt"] = pub_time
            filtered.append(n)

    filtered.sort(key=lambda n: n["_pub_dt"], reverse=True)
    return filtered


async def fetch_detail_batch(
    notice_ids: list[int],
    concurrency: int = 5,
) -> dict[int, dict]:
    """并发获取多条通知详情"""
    if not notice_ids:
        return {}

    p, browser, page = await _get_page()

    sem = asyncio.Semaphore(concurrency)

    async def worker(nid: int) -> tuple[int, dict | None]:
        async with sem:
            detail_page = await browser.new_page()
            try:
                await detail_page.goto(
                    f"{FRONTEND_URL}/notice/detail/{nid}",
                    wait_until="networkidle",
                    timeout=30000,
                )
                await asyncio.sleep(0.6)
                text = await detail_page.text_content("body") or ""
                text = _clean_text(text)
                return nid, {
                    "id": nid,
                    "full_text": text,
                    "url": f"{FRONTEND_URL}/notice/detail/{nid}",
                }
            except Exception as e:
                print(f"  [WARN] 详情获取失败 id={nid}: {e}")
                return nid, None
            finally:
                await detail_page.close()

    tasks = [worker(nid) for nid in notice_ids]
    results = await asyncio.gather(*tasks)
    await browser.close()
    await p.stop()

    return {nid: detail for nid, detail in results if detail is not None}


def _clean_text(text: str) -> str:
    """清理页面文本：提取核心内容，去掉导航/页脚噪音"""
    # 提取"通知详情"之后、页脚之前的内容
    text = text.replace("\r", "")

    # 找到"通知详情"的位置，取之后的内容
    idx = text.find("通知详情")
    if idx >= 0:
        text = text[idx + 4:]

    # 截掉页脚（© 2022 之后的）
    idx = text.find("© 2022")
    if idx >= 0:
        text = text[:idx]

    # 去掉"查看原文"及相邻的链接文字
    text = re.sub(r"查看原文\s*", "", text)

    # 合并多余空白
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]{3,}", "  ", text)

    # 去掉过短的行（导航残余）
    lines = text.split("\n")
    cleaned = []
    for line in lines:
        s = line.strip()
        if not s:
            cleaned.append(s)  # 保留空行做分隔
            continue
        # 纯 URL / 纯数字 / 太短且无意义
        if re.match(r"^https?://", s):
            continue
        if re.match(r"^\d{4,}$", s):
            continue
        if len(s) < 4 and not s[0].isalpha():
            continue
        cleaned.append(s)
    return "\n".join(cleaned).strip()


def _parse_publish_time(notice: dict) -> datetime | None:
    val = notice.get("publishTime")
    if not val:
        return None
    try:
        s = str(val).strip()
        dt = datetime.strptime(s[:19], "%Y-%m-%d %H:%M:%S")
        return dt.replace(tzinfo=CST)
    except Exception:
        return None


def enrich_notice_with_list_data(notice: dict) -> dict:
    """将列表 API 字段映射为通知字典"""
    return {
        "id": notice["id"],
        "title": notice.get("name", ""),
        "school": notice.get("school", ""),
        "college": notice.get("college", ""),
        "recruit_type": notice.get("recruitType", ""),
        "major_type": notice.get("majorType", ""),
        "end_time": notice.get("endTime", ""),
    }
