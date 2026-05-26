import datetime
from scraper import fetch_notices
from monitor import classify_notices, get_new_notices_classified
from notifier import send_bark_push
from config import DETAIL_PAGE_URL_TEMPLATE

LIST_PAGE_URL = "https://www.baoyantongzhi.com/notice"

def format_date(date_str):
    """
    格式化日期字符串，只保留年月日
    """
    if not date_str:
        return "未公布"
    try:
        dt = datetime.datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
        return dt.strftime("%Y-%m-%d")
    except Exception:
        return date_str

def main():
    print(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 开始执行保研信息监控...")
    
    # 1. 抓取最新的 100 条数据 (确保一整天内发布的数据全部被覆盖)
    raw_notices = fetch_notices(size=100)
    if not raw_notices:
        print("未获取到任何通知，本次运行结束。")
        return
        
    print(f"成功抓取到最新的 {len(raw_notices)} 条保研公告。")
    
    # 2. 对公告进行分类：集成电路类 vs 其他专业类
    ic_notices, other_notices = classify_notices(raw_notices)
    print(f"分类结果：集成电路相关公告 {len(ic_notices)} 条，其他专业公告 {len(other_notices)} 条。")
    
    # 3. 比对去重数据库，提取真正新增的公告
    new_ic, new_others, is_initialized = get_new_notices_classified(ic_notices, other_notices)
    print(f"增量结果：新增集成电路公告 {len(new_ic)} 条，新增其他专业公告 {len(new_others)} 条。")
    
    # 4. 进行消息推送
    if is_initialized:
        # A. 首次初始化运行，发送欢迎通知
        welcome_title = "💡 成功激活保研信息监控"
        welcome_body = (
            f"系统已成功部署！当前已在去重数据库中记录了 {len(ic_notices) + len(other_notices)} 条历史公告。\n"
            f"后续系统将在每晚 19:00 定时为您筛选并分类推送最新的夏令营和预推免通知。"
        )
        send_bark_push(welcome_title, welcome_body)
        
        # B. 发送集成电路的测试样例（最多 2 条）
        if new_ic:
            print("发送集成电路初始化样例推送...")
            for notice in new_ic[:2]:
                send_single_ic_push(notice, is_sample=True)
                
        # C. 发送其他专业的测试样例汇总（最多 3 条）
        if new_others:
            print("发送其他专业初始化样例推送...")
            send_others_summary_push(new_others[:3], is_sample=True)
            
    else:
        # B. 日常运行推送
        # 1. 集成电路新通知：逐个发送独立推送（附带直达报名链接）
        if new_ic:
            for notice in new_ic:
                send_single_ic_push(notice)
                
        # 2. 其他专业新通知：融合成一条汇总推送（附带列表页链接）
        if new_others:
            send_others_summary_push(new_others)
            
        if not new_ic and not new_others:
            print("今日无任何新增保研公告。")
            
    print("监控执行完毕。\n" + "="*40)

def send_single_ic_push(notice, is_sample=False):
    """
    发送单条集成电路相关公告推送
    """
    school = notice.get("school", "未知高校")
    college = notice.get("college", "未知学院")
    recruit_type = notice.get("recruitType", "公告")
    name = notice.get("name", "")
    end_time_str = format_date(notice.get("endTime"))
    
    url = notice.get("websiteUrl")
    if not url or not str(url).startswith("http"):
        url = DETAIL_PAGE_URL_TEMPLATE.format(id=notice.get("id"))
        
    prefix = "[测试样例] " if is_sample else ""
    title = f"{prefix}★集成电路★【{school}】{college} - {recruit_type}"
    body = f"项目：{name}\n截止时间：{end_time_str}"
    
    send_bark_push(title, body, url)

def send_others_summary_push(notices, is_sample=False):
    """
    将多条其他专业公告合并成一条汇总消息推送
    """
    count = len(notices)
    prefix = "[测试样例] " if is_sample else ""
    title = f"{prefix}【其他专业】今日新增 {count} 条保研公告"
    
    # 构造列表，最多展示前 15 条公告学校与学院
    lines = []
    max_display = 15
    for notice in notices[:max_display]:
        school = notice.get("school", "未知高校")
        college = notice.get("college", "未知学院")
        recruit_type = notice.get("recruitType", "公告")
        lines.append(f"• 【{school}】{college} - {recruit_type}")
        
    body = "\n".join(lines)
    if count > max_display:
        body += f"\n...等共 {count} 条公告"
        
    # 其他专业汇总推送一律跳转保研网列表主页
    send_bark_push(title, body, LIST_PAGE_URL)

if __name__ == "__main__":
    main()
