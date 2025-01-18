import requests
import random

def fetch_server_info(self):
    """通过 API 获取服务器地址和 token"""
    url = f"https://api.live.bilibili.com/xlive/web-room/v1/index/getDanmuInfo?id={self.room_id}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36",
        "Referer": f"https://live.bilibili.com/{self.room_id}",
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        data = response.json()
        if data['code'] == 0:
            self.token = data['data']['token']
            host_list = data['data']['host_list']
            self.ws_url = get_server_url(host_list)
            print(f"获取到 WebSocket 地址: {self.ws_url}")
            return True
    print("获取服务器信息失败")
    return False


def get_server_url(host_list):
    """从服务器列表中选择一个带 /sub 路径的 WebSocket 地址"""
    for host in host_list:
        if "broadcastlv" in host["host"]:
            return f"wss://{host['host']}:{host['wss_port']}/sub"
    server = random.choice(host_list)
    return f"wss://{server['host']}:{server['wss_port']}/sub"

