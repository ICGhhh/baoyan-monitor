"""
DeepSeek API 相关性分析 —— 判断通知是否与集成电路专业相关
"""
import json

from openai import OpenAI

from config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL

client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)

SYSTEM_PROMPT = """你是一个保研信息筛选助手。你的任务是判断保研夏令营/预推免通知是否与"集成电路"专业相关。

集成电路相关方向包括但不限于：
- 集成电路设计、集成电路工程、集成电路科学与工程
- 芯片设计、SoC、ASIC
- 模拟集成电路、数字集成电路、射频集成电路、混合信号集成电路
- 微电子学与固体电子学、微电子、微纳电子
- 半导体器件、半导体工艺、半导体材料
- EDA工具、电子设计自动化
- FPGA、VLSI（超大规模集成电路）
- 电子科学与技术（集成电路方向）
- 嵌入式系统（仅限芯片/IC硬件方向，纯软件开发不算）

不相关的情况：
- 纯计算机科学、软件工程、人工智能（与芯片无关的）
- 通信工程（非射频IC方向）
- 电力电子、电气工程
- 材料科学（非半导体材料）
- 纯机械、土木、生物医学等其他工科

请以 JSON 数组格式回答，每条包含三个字段：
- "id": 通知编号（整数）
- "relevant": true/false
- "reason": 一句话理由（中文，简洁）"""


def analyze(notices: list[dict]) -> list[dict]:
    """批量分析通知，返回相关性判断结果"""
    if not notices:
        return []

    # 构建用户消息：编号 + 标题 + 正文前500字
    items = []
    for n in notices:
        text = n.get("full_text", "")
        items.append(f"[{n['id']}] {text[:800]}")
    user_message = "请判断以下通知是否与集成电路专业相关：\n\n" + "\n\n---\n\n".join(items)

    try:
        resp = client.chat.completions.create(
            model=DEEPSEEK_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            temperature=0.1,
            max_tokens=2000,
        )
        raw = resp.choices[0].message.content or ""
        return _parse_response(raw, notices)

    except Exception as e:
        print(f"  [ERROR] DeepSeek API 调用失败: {e}")
        return []


def _parse_response(raw: str, notices: list[dict]) -> list[dict]:
    """解析 DeepSeek 返回的 JSON，兼容 markdown 代码块"""
    # 去掉可能的 markdown 代码块标记
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[-1]
        if raw.endswith("```"):
            raw = raw[:-3]
        raw = raw.strip()

    try:
        results = json.loads(raw)
        if isinstance(results, dict):
            results = [results]
        return results
    except json.JSONDecodeError:
        pass

    # 回退：逐行解析
    results = []
    for line in raw.split("\n"):
        line = line.strip()
        if not line:
            continue
        try:
            r = json.loads(line)
            if isinstance(r, dict):
                results.append(r)
        except json.JSONDecodeError:
            pass

    return results
