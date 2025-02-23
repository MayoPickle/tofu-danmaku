import json
import zlib
import brotli
import requests

KEYWORDS = ["观测站", "鱼豆腐"]

class BiliMessageParser:
    def __init__(self, room_id):
        self.room_id = room_id
        self.post_url = "http://192.168.0.101:8083"

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

                if protover == 2:  # zlib 压缩消息
                    decompressed_data = zlib.decompress(body)
                    self.parse_message(decompressed_data)
                elif protover == 3:  # brotli 压缩消息
                    decompressed_data = brotli.decompress(body)
                    self.parse_message(decompressed_data)
                elif protover in (0, 1):  # 普通消息
                    if operation == 5:  # 弹幕消息或其他事件
                        messages = json.loads(body.decode("utf-8"))
                        self.handle_danmaku(messages)
                    elif operation == 3:  # 心跳回复
                        popularity = int.from_bytes(body, "big")
                offset += packet_length
        except Exception as e:
            print(f"❌ 消息解析错误: {e}")

    def handle_danmaku(self, messages):
        """处理弹幕消息或其他事件"""
        try:
            if isinstance(messages, dict):
                cmd = messages.get("cmd", "")

                # ✅ 处理弹幕消息
                if cmd == "DANMU_MSG":
                    comment = messages["info"][1]  # 弹幕内容
                    username = messages["info"][2][1]  # 发送弹幕的用户
                    print(f"[{username}] {comment}")
                    self.keyword_detection(comment)

                # ✅ 处理 PK_BATTLE_PROCESS_NEW 事件
                elif cmd == "PK_BATTLE_START_NEW":
                    self.handle_pk_battle_process_new(messages)

        except Exception as e:
            print(f"❌ 处理消息时发生错误: {e}")

    def keyword_detection(self, danmaku):
        """检测弹幕内容是否包含关键字并发送 POST 请求"""
        if any(keyword in danmaku for keyword in KEYWORDS):
            post_url = f"{self.post_url}/ticket"
            payload = {
                "room_id": self.room_id,
                "danmaku": danmaku
            }
            try:
                response = requests.post(post_url, json=payload, timeout=3)
                if response.status_code == 200:
                    print(f"✅ 关键字检测成功：'{danmaku}' 已发送至 {post_url}")
                else:
                    print(f"❌ 发送失败，HTTP 状态码: {response.status_code}")
            except requests.RequestException as e:
                print(f"❌ 发送失败，错误: {e}")

    def handle_pk_battle_process_new(self, messages):
        """处理 PK_BATTLE_PROCESS_NEW 事件，并向 /pk_wanzun 发送 POST 请求"""
        post_url = f"{self.post_url}/pk_wanzun"

        # 发送 PK_INFO 消息体作为 payload
        payload = {
            "room_id": self.room_id,
            "pk_battle_process_new": messages["data"],
            "token": "8096"
        }

        try:
            response = requests.post(post_url, json=payload, timeout=3)
            if response.status_code == 200:
                print(f"✅ PK_BATTLE_PROCESS_NEW 已成功发送至 {post_url}")
            else:
                print(f"❌ PK_BATTLE_PROCESS_NEW 发送失败，HTTP 状态码: {response.status_code}")
        except requests.RequestException as e:
            print(f"❌ PK_BATTLE_PROCESS_NEW 发送失败，错误: {e}")
