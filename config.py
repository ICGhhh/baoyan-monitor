import os

# ── 后端 API 地址 ──
API_BASE = "https://ajqwsiasyqyi.sealosgzg.site"

# ── 抓取配置 ──
NOTICE_YEAR = 2026
FETCH_SIZE = 60               # 每次抓取条数（取新不取多）
LOOKBACK_DAYS = 14            # 只处理最近 N 天发布的

# ── 监控截止 ──
MONITOR_END_DATE = "2026-09-30"

# ── DeepSeek API ──
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"
DEEPSEEK_MODEL = "deepseek-chat"

# ── QQ邮箱 SMTP ──
SMTP_HOST = "smtp.qq.com"
SMTP_PORT = 465
SMTP_USER = os.environ.get("QQ_EMAIL", "")
SMTP_PASS = os.environ.get("QQ_SMTP_CODE", "")
RECIPIENT = os.environ.get("QQ_EMAIL", "")

# ── 持久化文件路径 ──
SEEN_FILE = os.path.join(os.path.dirname(__file__), "seen.json")
