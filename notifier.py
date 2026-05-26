import requests
from config import BARK_KEY

def print_safe(msg):
    """
    安全打印函数，防止在 GBK 编码的 Windows 终端下打印 Emoji 时抛出 UnicodeEncodeError。
    """
    try:
        print(msg)
    except UnicodeEncodeError:
        try:
            print(msg.encode('gbk', 'ignore').decode('gbk'))
        except Exception:
            # 极度防线，防止一切意料之外的打印错误
            pass

def send_bark_push(title, body, url=None):
    """
    通过 Bark 服务向 iPhone 发送系统推送通知。
    :param title: 推送标题
    :param body: 推送内容
    :param url: 点击推送后跳转的 URL（可选）
    :return: 是否发送成功
    """
    if not BARK_KEY:
        print_safe("未检测到 BARK_KEY，跳过消息发送。请在环境变量中配置 BARK_KEY。")
        print_safe(f"[本地模拟推送]\n标题: {title}\n内容: {body}\n跳转链接: {url}\n")
        return False
        
    endpoint = "https://api.day.app/push"
    
    payload = {
        "title": title,
        "body": body,
        "device_key": BARK_KEY,
        "group": "保研通知",
        "icon": "https://www.baoyantongzhi.com/favicon.ico"
    }
    
    if url:
        payload["url"] = url
        
    headers = {
        "Content-Type": "application/json; charset=utf-8"
    }
    
    try:
        response = requests.post(endpoint, json=payload, headers=headers, timeout=10)
        if response.status_code == 200:
            res_data = response.json()
            if res_data.get("code") == 200:
                print_safe(f"推送成功: {title}")
                return True
            else:
                print_safe(f"推送失败，Bark 错误码: {res_data.get('code')}, 消息: {res_data.get('message')}")
        else:
            print_safe(f"推送请求失败，状态码: {response.status_code}, 响应: {response.text}")
    except Exception as e:
        print_safe(f"推送网络连接异常: {e}")
        
    return False

if __name__ == "__main__":
    # 本地运行进行推送连通性测试
    # 注意：需要先在系统环境变量中设置 BARK_KEY (Windows下可以：set BARK_KEY=your_key)
    send_bark_push("保研监控系统", "这是一条测试推送消息。如果您收到了，说明配置完全成功！", "https://www.baoyantongzhi.com")
