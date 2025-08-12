import websocket
import threading
import time
import logging
import sys
from websocket import ABNF
from typing import Optional

from .fetch import fetch_server_info
from .packet import create_handshake_packet, create_heartbeat_packet
from .parser_handler import BiliMessageParser
from .config import API_BASE_URL

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)  # 明确指定输出到 stdout
    ]
)
logger = logging.getLogger(__name__)

# 确保日志立即输出
logging.getLogger().handlers[0].flush = lambda: sys.stdout.flush()


class BiliDanmakuClient:
    def __init__(self, room_id, spider=False, api_base_url=None, debug_events: bool = False, cookie: Optional[str] = None, debug_ws: bool = False):
        self.room_id = room_id  # 房间号
        self.spider = spider    # 是否启用爬虫功能
        self.ws_url = None      # WebSocket 地址
        self.token = None       # 动态获取的 token 
        self.ws = None
        self.heartbeat_interval = 30  # 心跳间隔时间（秒）
        self.api_base_url = api_base_url
        self.debug_events = bool(debug_events)
        self.cookie_str = cookie
        self.cookies = self._parse_cookie_string(cookie) if cookie else {}
        self.debug_ws = bool(debug_ws)
        # 从 Cookie 中提取用户UID（如有）
        try:
            self.user_uid = int(self.cookies.get('DedeUserID', '0')) if self.cookies else 0
        except Exception:
            self.user_uid = 0
        # 将在 fetch_server_info 中填充 buvid3/4
        self.buvid3 = ''
        self.buvid4 = ''
        self.heartbeat_started = False
        self.parser = BiliMessageParser(
            room_id,
            api_base_url=self.api_base_url or API_BASE_URL,
            spider=bool(spider),
            debug_events=self.debug_events,
            on_authenticated=self.on_auth_success
        )
        
        if spider:
            logger.info("🕷️ 直播间爬虫功能已启用")
        else:
            logger.info("ℹ️ 直播间爬虫功能未启用")

    @staticmethod
    def _parse_cookie_string(cookie_str: str) -> dict:
        """将形如 "k1=v1; k2=v2" 的Cookie字符串解析为dict"""
        cookies = {}
        try:
            for part in cookie_str.split(';'):
                if not part.strip():
                    continue
                if '=' in part:
                    k, v = part.split('=', 1)
                    cookies[k.strip()] = v.strip()
        except Exception:
            pass
        return cookies

    def fetch_server_info(self):
        return fetch_server_info(self)

    def create_handshake_packet(self):
        return create_handshake_packet(self)

    def create_heartbeat_packet(self):
        return create_heartbeat_packet()

    def send_heartbeat(self):
        """定时发送心跳包"""
        while self.ws:
            try:
                self.ws.send(self.create_heartbeat_packet(), ABNF.OPCODE_BINARY)
                time.sleep(self.heartbeat_interval)
            except Exception:
                break

    def on_open(self, ws):
        logger.info("✅ WebSocket 连接已建立")
        handshake_packet = self.create_handshake_packet()
        ws.send(handshake_packet, ABNF.OPCODE_BINARY)
        logger.info("✅ 认证包发送成功")

    def on_auth_success(self):
        """认证成功后启动心跳，不要在 on_open 里就发，避免早发导致被断开"""
        if not self.heartbeat_started:
            self.heartbeat_started = True
            threading.Thread(target=self.send_heartbeat, daemon=True).start()
            logger.info("✅ 已收到认证通过，启动心跳线程")

    def on_message(self, ws, message):
        self.parser.parse_message(message)

    def on_error(self, ws, error):
        logger.error(f"❌ WebSocket 错误: {error}")

    def on_close(self, ws, close_status_code, close_msg):
        logger.info(f"❌ WebSocket 连接已关闭，状态码: {close_status_code}, 原因: {close_msg}")

    def start(self):
        if not self.fetch_server_info():
            return

        if self.debug_ws:
            logger.info(f"[WS] 即将连接: url={self.ws_url}")

        self.ws = websocket.WebSocketApp(
            self.ws_url,
            on_open=self.on_open,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close,
            header=[
                "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36",
                "Origin: https://live.bilibili.com",
            ]
        )

        if self.debug_ws:
            websocket.enableTrace(True)
            logger.info("[WS] Trace 已启用（底层帧将打印到stdout）")

        self.ws.run_forever()
