import json
import zlib
import brotli
import requests
import threading

KEYWORDS = ["观测站", "鱼豆腐"]

class PKBattleHandler:
    def __init__(self, room_id, post_url, battle_type=1):
        self.room_id = room_id
        self.post_url = post_url
        self.last_pk_info = None
        self.pk_triggered = False

        # 根据 battle_type 决定 timer_230 的时间
        delay_time = 170 if battle_type == 2 else 230
        self.timer_230 = threading.Timer(delay_time, self.delayed_check_230)
        self.timer_290 = threading.Timer(290, self.delayed_check_290)

        self.timer_230.start()
        self.timer_290.start()

        print(f"✅ PKBattleHandler 初始化，定时器已启动 (battle_type={battle_type}, delay_time={delay_time}s)")

    def update_info(self, pk_info_message):
        """更新最新的 PK_INFO 消息"""
        self.last_pk_info = pk_info_message
        print("✅ PKBattleHandler 更新了 PK_INFO 信息")

    def delayed_check_230(self):
        """3分50秒或 170 秒检查逻辑"""
        print("⏱️ 延时检查开始")
        if self.pk_triggered:
            return
        if self.last_pk_info:
            try:
                members = self.last_pk_info["data"]["members"]
                self_participant = None
                opponent = None

                for member in members:
                    if member["room_id"] == self.room_id:
                        self_participant = member
                    else:
                        opponent = member

                if self_participant and opponent:
                    golds_self = self_participant.get("golds", 0)
                    votes_opponent = opponent.get("votes", 0)

                    if golds_self == 0 and votes_opponent > 100:
                        print("❗ 条件满足，触发 API")
                        self.pk_triggered = True
                        self.cancel_timer_290()
                        self.trigger_api()
                    else:
                        print("✅ 条件不满足")
            except Exception as e:
                print(f"❌ 延时检查出错: {e}")
        else:
            print("❗ 未收到 PK_INFO，不触发 API")

    def delayed_check_290(self):
        """4分50秒检查逻辑"""
        print("⏱️ 4分50秒延时检查开始")
        if self.pk_triggered:
            return
        if not self.last_pk_info:
            print("❗ 未收到 PK_INFO，触发 API")
            self.pk_triggered = True
            self.trigger_api()
        else:
            try:
                members = self.last_pk_info["data"]["members"]
                self_participant = next(
                    (member for member in members if member["room_id"] == self.room_id), None
                )

                if self_participant:
                    golds_self = self_participant.get("golds", 0)
                    if golds_self == 0:
                        print("❗ 条件满足，触发 API")
                        self.pk_triggered = True
                        self.trigger_api()
                    else:
                        print("✅ 条件不满足")
            except Exception as e:
                print(f"❌ 4分50秒检查出错: {e}")
                self.pk_triggered = True
                self.trigger_api()

    def cancel_timer_290(self):
        """取消 4分50秒定时器"""
        if self.timer_290:
            self.timer_290.cancel()
            print("✅ 已取消 4分50秒定时器")

    def stop(self):
        """停止定时器并销毁实例"""
        if self.timer_230:
            self.timer_230.cancel()
        if self.timer_290:
            self.timer_290.cancel()
        print("🛑 定时器已取消，PKBattleHandler 实例销毁")

    def trigger_api(self):
        """触发 API，向 /pk_wanzun 发送 POST 请求"""
        post_url = f"{self.post_url}/pk_wanzun"
        payload = {
            "room_id": self.room_id,
            "pk_battle_process_new": self.last_pk_info["data"] if self.last_pk_info else {},
            "token": "8096"
        }
        try:
            response = requests.post(post_url, json=payload, timeout=3)
            if response.status_code == 200:
                print(f"✅ API 已成功发送至 {post_url}")
            else:
                print(f"❌ API 发送失败，HTTP 状态码: {response.status_code}")
        except requests.RequestException as e:
            print(f"❌ API 发送异常: {e}")


class BiliMessageParser:
    def __init__(self, room_id):
        self.room_id = room_id
        self.post_url = "http://192.168.0.101:8081"
        self.current_pk_handler = None

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

                if protover == 2:
                    decompressed_data = zlib.decompress(body)
                    self.parse_message(decompressed_data)
                elif protover == 3:
                    decompressed_data = brotli.decompress(body)
                    self.parse_message(decompressed_data)
                elif protover in (0, 1):
                    if operation == 5:
                        messages = json.loads(body.decode("utf-8"))
                        self.handle_danmaku(messages)
                    elif operation == 3:
                        popularity = int.from_bytes(body, "big")
                offset += packet_length
        except Exception as e:
            print(f"❌ 消息解析错误: {e}")

    def handle_danmaku(self, messages):
        """处理弹幕消息或其他事件"""
        try:
            if isinstance(messages, dict):
                cmd = messages.get("cmd", "")
                if cmd == "DANMU_MSG":
                    comment = messages["info"][1]
                    username = messages["info"][2][1]
                    print(f"[{username}] {comment}")
                    self.keyword_detection(comment)
                elif cmd == "PK_INFO":
                    if self.current_pk_handler:
                        self.current_pk_handler.update_info(messages)
                elif cmd == "PK_BATTLE_START_NEW":
                    print("✅ 收到 PK_BATTLE_START_NEW 消息")
                    self.current_pk_handler = PKBattleHandler(self.room_id, self.post_url)
                elif cmd == "PK_BATTLE_END":
                    print("🛑 收到 PK_BATTLE_END 消息，销毁 PKBattleHandler 实例")
                    if self.current_pk_handler:
                        self.current_pk_handler.stop()
                        self.current_pk_handler = None
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
