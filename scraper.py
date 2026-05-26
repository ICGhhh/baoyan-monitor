import requests
import datetime
from config import API_BASE_URL

def fetch_notices(size=50, year=None):
    """
    从保研通知网后台接口获取通知列表。
    :param size: 每次获取的数据量，默认 50 条，足够覆盖每日更新
    :param year: 查询的年份，如果不指定，默认使用当前年份
    :return: 包含通知字典的列表，获取失败时返回空列表
    """
    if year is None:
        year = datetime.date.today().year

    params = {
        'current': 1,
        'size': size,
        'year': year
    }
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Content-Type': 'application/json',
        'Origin': 'https://www.baoyantongzhi.com',
        'Referer': 'https://www.baoyantongzhi.com/'
    }
    
    try:
        response = requests.get(API_BASE_URL, params=params, headers=headers, timeout=15)
        if response.status_code == 200:
            data = response.json()
            if data.get("code") == 200 or data.get("code") == 0:
                records = data.get("data", {}).get("records", [])
                return records
            else:
                print(f"API 返回错误代码: {data.get('code')}, 消息: {data.get('msg')}")
        else:
            print(f"请求失败，状态码: {response.status_code}, 响应: {response.text}")
    except Exception as e:
        print(f"请求网络异常: {e}")
        
    return []

if __name__ == "__main__":
    # 本地单独运行测试
    notices = fetch_notices(size=5)
    print(f"测试获取通知，数量: {len(notices)}")
    if notices:
        print("第一条通知样例:")
        import json
        print(json.dumps(notices[0], indent=2, ensure_ascii=False))
