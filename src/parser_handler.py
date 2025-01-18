import json
import zlib
import brotli

def parse_message(self, data):
    """解析服务器返回的消息"""
    try:
        offset = 0
        while offset < len(data):
            packet_length = int.from_bytes(data[offset:offset + 4], "big")
            header_length = int.from_bytes(data[offset + 4:offset + 6], "big")
            protover = int.from_bytes(data[offset + 6:offset + 8], "big")
            operation = int.from_bytes(data[offset + 8:offset + 12], "big")
            body = data[offset + header_length:offset + packet_length]

            if protover == 2:  # zlib压缩消息
                decompressed_data = zlib.decompress(body)
                parse_message(self, decompressed_data)
            elif protover == 3:  # brotli压缩消息
                decompressed_data = brotli.decompress(body)
                parse_message(self, decompressed_data)
            elif protover in (0, 1):  # 普通消息
                if operation == 5:  # 弹幕消息
                    messages = json.loads(body.decode("utf-8"))
                    self.handle_danmaku(messages)
                elif operation == 3:  # 心跳回复
                    popularity = int.from_bytes(body, "big")
                    print(f"当前人气值: {popularity}")
            offset += packet_length
    except Exception:
        pass  # 忽略解析错误


def handle_danmaku(self, messages):
    """处理弹幕消息"""
    try:
        if isinstance(messages, dict):
            cmd = messages.get("cmd", "")
            if cmd == "DANMU_MSG":
                comment = messages["info"][1]
                username = messages["info"][2][1]
                print(f"[{username}] {comment}")
    except Exception:
        pass  # 忽略弹幕解析错误

