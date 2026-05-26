import json
import os
from config import KEYWORDS, DB_FILE

def classify_notices(notices):
    """
    将通知列表分类为集成电路相关和其他专业。
    匹配标题(name)、学院(college)和学校(school)。
    返回: (ic_notices, other_notices)
    """
    ic_notices = []
    other_notices = []
    
    for notice in notices:
        name = str(notice.get("name", "")).lower()
        college = str(notice.get("college", "")).lower()
        school = str(notice.get("school", "")).lower()
        
        # 检查是否包含任何关键词
        is_ic = False
        for kw in KEYWORDS:
            kw_lower = kw.lower()
            if kw_lower in name or kw_lower in college or kw_lower in school:
                is_ic = True
                break
                
        if is_ic:
            ic_notices.append(notice)
        else:
            other_notices.append(notice)
            
    return ic_notices, other_notices

def load_sent_ids():
    """
    从本地 JSON 文件读取已发送通知的 ID 列表。
    """
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"读取去重数据库失败，正在重新初始化: {e}")
            return []
    return None  # None 表示数据库文件不存在（首次运行）

def save_sent_ids(sent_ids):
    """
    保存已发送通知的 ID 列表到本地 JSON 文件，并限制数据库最大长度为 3000，防止文件过大。
    """
    try:
        # 去重并排序
        unique_ids = sorted(list(set(sent_ids)))
        
        # 如果超出 3000 条，只保留最近的 3000 条 (假设较大的 ID 是较新的，这里简单截取)
        if len(unique_ids) > 3000:
            unique_ids = unique_ids[-3000:]
            
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(unique_ids, f, indent=2, ensure_ascii=False)
        print(f"成功保存 {len(unique_ids)} 个通知 ID 到去重数据库。")
    except Exception as e:
        print(f"写入去重数据库失败: {e}")

def get_new_notices_classified(ic_notices, other_notices):
    """
    比对数据库，筛选出两类中真正全新未推送的通知，并更新数据库。
    返回: (new_ic, new_others, is_initialized)
    """
    sent_ids = load_sent_ids()
    is_initialized = False
    
    # 首次运行：初始化数据库
    if sent_ids is None:
        print("首次运行，正在初始化去重数据库...")
        # 将当前获取到的所有公告 ID 都记入数据库，防止产生大量历史推送
        all_ids = [notice["id"] for notice in ic_notices + other_notices]
        save_sent_ids(all_ids)
        
        # 首次初始化时，各取最多 3 条作为样例展示给用户，以验证效果
        return ic_notices[:2], other_notices[:3], True
        
    new_ic = []
    new_others = []
    updated_sent_ids = list(sent_ids)
    
    # 筛选集成电路新公告
    for notice in ic_notices:
        notice_id = notice["id"]
        if notice_id not in sent_ids:
            new_ic.append(notice)
            updated_sent_ids.append(notice_id)
            
    # 筛选其他专业新公告
    for notice in other_notices:
        notice_id = notice["id"]
        if notice_id not in sent_ids:
            new_others.append(notice)
            updated_sent_ids.append(notice_id)
            
    # 如果有任何新公告，更新数据库
    if new_ic or new_others:
        save_sent_ids(updated_sent_ids)
        
    return new_ic, new_others, False
