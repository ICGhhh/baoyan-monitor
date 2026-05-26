import os

# 目标网站配置
API_BASE_URL = "https://ajqwsiasyqyi.sealosgzg.site/backgd/notice/show/list"
DETAIL_PAGE_URL_TEMPLATE = "https://www.baoyantongzhi.com/notice/detail/{id}"

# 筛选关键词（不区分大小写）
KEYWORDS = [
    '集成电路', 
    '微电子', 
    '芯片', 
    '半导体', 
    '电子科学与技术', 
    '电子信息', 
    '电科', 
    'IC', 
    'ASIC', 
    'FPGA'
]

# Bark 配置
# 从环境变量中读取 Bark Key，如果本地开发没有设置，可以使用占位符
BARK_KEY = os.environ.get("BARK_KEY", "")

# 去重数据库/文件名
DB_FILE = "sent_notices.json"
