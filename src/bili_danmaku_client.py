import websocket
import threading
import time
import logging
import sys
from websocket import ABNF

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
    def __init__(self, room_id, spider=False, api_base_url=None, debug_events: bool = False):
        self.room_id = room_id  # 房间号
        self.spider = spider    # 是否启用爬虫功能
        self.ws_url = None      # WebSocket 地址
        self.token = None       # 动态获取的 token 
        self.ws = None
        self.heartbeat_interval = 30  # 心跳间隔时间（秒）
        self.api_base_url = api_base_url
        self.debug_events = bool(debug_events)
        self.parser = BiliMessageParser(
            room_id,
            api_base_url=self.api_base_url or API_BASE_URL,
            spider=bool(spider),
            debug_events=self.debug_events
        )
        
        if spider:
            logger.info("🕷️ 直播间爬虫功能已启用")
        else:
            logger.info("ℹ️ 直播间爬虫功能未启用")

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
        threading.Thread(target=self.send_heartbeat, daemon=True).start()

    def on_message(self, ws, message):
        self.parser.parse_message(message)

    def on_error(self, ws, error):
        logger.error(f"❌ WebSocket 错误: {error}")

    def on_close(self, ws, close_status_code, close_msg):
        logger.info(f"❌ WebSocket 连接已关闭，状态码: {close_status_code}, 原因: {close_msg}")

    def start(self):
        if not self.fetch_server_info():
            return

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
        self.ws.run_forever()
