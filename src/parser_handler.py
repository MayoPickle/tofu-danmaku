import json
import zlib
import brotli
import requests
import threading

KEYWORDS = ["观测站", "鱼豆腐"]

class PKBattleHandler:
    """
    单次 PK 逻辑处理器，每次 PK_BATTLE_START_NEW 事件创建一个实例，
    内部启动两个定时器分别在 230 秒和 290 秒时检查 PK_INFO 状态，
    满足条件则触发 API，触发后内部状态置为已激活。
    """
    def __init__(self, room_id, post_url):
        self.room_id = room_id
        self.post_url = post_url
        self.last_pk_info = None
        self.pk_triggered = False
        self.timer_230 = threading.Timer(230, self.delayed_check_230)
        self.timer_290 = threading.Timer(290, self.delayed_check_290)
        self.timer_230.start()
        self.timer_290.start()
        print("✅ PKBattleHandler 初始化，定时器已启动")

    def update_info(self, pk_info_message):
        """更新最新的 PK_INFO 消息"""
        self.last_pk_info = pk_info_message
        print("✅ PKBattleHandler 更新了 PK_INFO 信息")

    def delayed_check_230(self):
        """3分50秒时检查：若参与者2的 votes > 100 且参与者1的 golds == 0，则触发 API并取消 4分50秒定时器"""
        print("⏱️ 3分50秒延时检查开始")
        if self.pk_triggered:
            return
        if self.last_pk_info:
            try:
                members = self.last_pk_info["data"]["members"]
                participant1 = members[0]
                participant2 = members[1]
                golds1 = participant1.get("golds", 0)
                votes2 = participant2.get("votes", 0)
                if golds1 == 0 and votes2 > 100:
                    print("❗ 3分50秒条件满足：参与者2的 votes > 100 且参与者1的 golds == 0，触发 API")
                    self.pk_triggered = True
                    self.cancel_timer_290()
                    self.trigger_api()
                else:
                    print("✅ 3分50秒条件不满足，不触发 API")
            except Exception as e:
                print(f"❌ 3分50秒检查时出错: {e}")
        else:
            print("❗ 3分50秒未收到 PK_INFO，不触发 API")

    def delayed_check_290(self):
        """4分50秒时检查：若参与者1的 golds == 0，则触发 API（前提是 3分50秒未触发）"""
        print("⏱️ 4分50秒延时检查开始")
        if self.pk_triggered:
            return
        if not self.last_pk_info:
            print("❗ 4分50秒未收到 PK_INFO，触发 API")
            self.pk_triggered = True
            self.trigger_api()
        else:
            try:
                participant1 = self.last_pk_info["data"]["members"][0]
                golds1 = participant1.get("golds", 0)
                if golds1 == 0:
                    print("❗ 4分50秒条件满足：参与者1的 golds == 0，触发 API")
                    self.pk_triggered = True
                    self.trigger_api()
                else:
                    print("✅ 4分50秒条件不满足，不触发 API")
            except Exception as e:
                print(f"❌ 4分50秒检查时出错: {e}")
                self.pk_triggered = True
                self.trigger_api()

    def cancel_timer_290(self):
        """取消 4分50秒定时器"""
        if self.timer_290:
            self.timer_290.cancel()
            print("✅ 已取消 4分50秒定时器")

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
                print(f"✅ PK_BATTLE_PROCESS_NEW API 已成功发送至 {post_url}")
            else:
                print(f"❌ PK_BATTLE_PROCESS_NEW API 发送失败，HTTP 状态码: {response.status_code}")
        except requests.RequestException as e:
            print(f"❌ PK_BATTLE_PROCESS_NEW API 发送异常: {e}")
        # 触发后不再做其它处理，此实例后续会随着引用消失而被销毁

class BiliMessageParser:
    def __init__(self, room_id):
        self.room_id = room_id
        self.post_url = "http://192.168.0.101:8081"
        # 当前的 PKBattleHandler（每次 PK_BATTLE_START_NEW 时创建新对象）
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
                if cmd == "DANMU_MSG":
                    comment = messages["info"][1]
                    username = messages["info"][2][1]
                    print(f"[{username}] {comment}")
                    self.keyword_detection(comment)
                elif cmd == "PK_INFO":
                    print("✅ 收到 PK_INFO 消息")
                    if self.current_pk_handler:
                        self.current_pk_handler.update_info(messages)
                elif cmd == "PK_BATTLE_START_NEW":
                    print("✅ 收到 PK_BATTLE_START_NEW 消息")
                    # 每次触发时创建一个新的 PKBattleHandler 对象，之前的对象不再引用，将自动销毁
                    self.current_pk_handler = PKBattleHandler(self.room_id, self.post_url)
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
