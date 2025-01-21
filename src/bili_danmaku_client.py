import websocket
import threading
import time
from websocket import ABNF

from .fetch import fetch_server_info
from .packet import create_handshake_packet, create_heartbeat_packet
from .parser_handler import parse_message, handle_danmaku

class BiliDanmakuClient:
    def __init__(self, room_id):
        self.room_id = room_id  # 房间号
        self.ws_url = None      # WebSocket 地址
        self.token = None       # 动态获取的 token
        self.ws = None
        self.heartbeat_interval = 30  # 心跳间隔时间（秒）

    def fetch_server_info(self):
        return fetch_server_info(self)

    def create_handshake_packet(self):
        return create_handshake_packet(self)

    def create_heartbeat_packet(self):
        return create_heartbeat_packet()

    def parse_message(self, data):
        return parse_message(self, data)

    def handle_danmaku(self, messages):
        return handle_danmaku(self, messages)

    def send_heartbeat(self):
        """定时发送心跳包"""
        while self.ws:
            try:
                self.ws.send(self.create_heartbeat_packet(), ABNF.OPCODE_BINARY)
                time.sleep(self.heartbeat_interval)
            except Exception:
                break

    def on_open(self, ws):
        print("WebSocket 连接已建立")
        handshake_packet = self.create_handshake_packet()
        ws.send(handshake_packet, ABNF.OPCODE_BINARY)
        print("认证包发送成功")
        threading.Thread(target=self.send_heartbeat, daemon=True).start()

    def on_message(self, ws, message):
        self.parse_message(message)

    def on_error(self, ws, error):
        print(f"WebSocket 错误: {error}")

    def on_close(self, ws, close_status_code, close_msg):
        print(f"WebSocket 连接已关闭，状态码: {close_status_code}, 原因: {close_msg}")

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

