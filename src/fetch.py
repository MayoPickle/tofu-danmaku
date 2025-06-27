import requests
import random
import time
import logging
from .wbi_sign import get_wbi_sign, extract_key_from_url

logger = logging.getLogger(__name__)

def fetch_buvid():
    """获取 buvid3 和 buvid4"""
    url = "https://api.bilibili.com/x/frontend/finger/spi"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://www.bilibili.com/"
    }
    
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            if data.get('code') == 0 and 'data' in data:
                return {
                    'buvid3': data['data'].get('b_3', ''),
                    'buvid4': data['data'].get('b_4', '')
                }
    except Exception as e:
        logger.warning(f"获取 buvid 失败: {e}")
    
    return {'buvid3': '', 'buvid4': ''}

def fetch_wbi_keys():
    """获取 WBI 密钥的统一方法"""
    # 获取 buvid3 和 buvid4
    buvid_data = fetch_buvid()
    cookies = {}
    if buvid_data['buvid3']:
        cookies['buvid3'] = buvid_data['buvid3']
    if buvid_data['buvid4']:
        cookies['buvid4'] = buvid_data['buvid4']
    
    # 方法1: 从导航API获取（需要cookie但不需要登录）
    url = "https://api.bilibili.com/nav"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://www.bilibili.com/"
    }
    
    try:
        response = requests.get(url, headers=headers, cookies=cookies)
        if response.status_code == 200:
            data = response.json()
            if data.get('code') == 0 and 'data' in data:
                wbi_img = data['data'].get('wbi_img', {})
                if wbi_img and 'img_url' in wbi_img and 'sub_url' in wbi_img:
                    return {
                        'img_url': wbi_img['img_url'],
                        'sub_url': wbi_img['sub_url']
                    }
    except Exception:
        pass
    
    # 方法2: 使用默认的WBI密钥（这些是公开的默认值）
    return {
        'img_url': 'https://i0.hdslb.com/bfs/wbi/7cd084941338484aae1ad9425b84077c.png',
        'sub_url': 'https://i0.hdslb.com/bfs/wbi/4932caff0ff746eab6f01bf08b70ac45.png'
    }

def fetch_server_info(self):
    """通过 API 获取服务器地址和 token"""
    # 获取 buvid3 和 buvid4
    buvid_data = fetch_buvid()
    logger.info(f"获取到 buvid3: {buvid_data['buvid3'][:20]}..., buvid4: {buvid_data['buvid4'][:20]}...")
    
    # 获取 WBI 密钥
    wbi_keys = fetch_wbi_keys()
    
    # 准备请求参数
    timestamp = int(time.time())
    params = {
        "id": str(self.room_id),
        "type": "0",
        "wts": str(timestamp),
        "web_location": "444.8"
    }
    
    # 添加 WBI 签名
    if wbi_keys:
        img_key = extract_key_from_url(wbi_keys['img_url'])
        sub_key = extract_key_from_url(wbi_keys['sub_url'])
        wbi_sign = get_wbi_sign(params, img_key, sub_key)
        params['w_rid'] = wbi_sign
    
    url = "https://api.live.bilibili.com/xlive/web-room/v1/index/getDanmuInfo"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": f"https://live.bilibili.com/{self.room_id}",
        "Origin": "https://live.bilibili.com"
    }
    
    # 准备 cookies
    cookies = {}
    if buvid_data['buvid3']:
        cookies['buvid3'] = buvid_data['buvid3']
    if buvid_data['buvid4']:
        cookies['buvid4'] = buvid_data['buvid4']
    
    try:
        response = requests.get(url, headers=headers, params=params, cookies=cookies)
        
        if response.status_code == 200:
            data = response.json()
            
            if data['code'] == 0:
                self.token = data['data']['token']
                host_list = data['data']['host_list']
                self.ws_url = get_server_url(host_list)
                logger.info(f"✅ 获取到 WebSocket 地址: {self.ws_url}")
                return True
            else:
                logger.error(f"API 返回错误 - code: {data['code']}, message: {data.get('message', '未知错误')}")
                
                # 如果是 -352 错误，尝试不带签名的请求
                if data['code'] == -352:
                    logger.info("尝试不带 WBI 签名的请求...")
                    params_no_wbi = {
                        "id": str(self.room_id),
                        "type": "0"
                    }
                    response = requests.get(url, headers=headers, params=params_no_wbi, cookies=cookies)
                    if response.status_code == 200:
                        data = response.json()
                        if data['code'] == 0:
                            self.token = data['data']['token']
                            host_list = data['data']['host_list']
                            self.ws_url = get_server_url(host_list)
                            logger.info(f"✅ 获取到 WebSocket 地址（无WBI）: {self.ws_url}")
                            return True
    except Exception as e:
        logger.error(f"获取服务器信息失败: {e}")
    
    return False


def get_server_url(host_list):
    """从服务器列表中选择一个带 /sub 路径的 WebSocket 地址"""
    for host in host_list:
        if "broadcastlv" in host["host"]:
            return f"wss://{host['host']}:{host['wss_port']}/sub"
    server = random.choice(host_list)
    return f"wss://{server['host']}:{server['wss_port']}/sub"

