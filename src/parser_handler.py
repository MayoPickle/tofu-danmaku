import json
import zlib
import brotli
import requests
import threading


KEYWORDS = ["观测站", "鱼豆腐"]


class PKBattleHandler:
    def __init__(self, room_id, post_url, battle_type):
        self.room_id = room_id
        self.post_url = post_url
        self.battle_type = battle_type  # 新增：根据 PK 类型决定对比策略
        self.last_pk_info = None
        self.last_battle_process = None
        self.pk_triggered = False

        # 根据 battle_type 启动不同的计时器
        if self.battle_type == 1:
            self.kill_pk_timer = threading.Timer(170, self.delayed_check)
        else:
            self.kill_pk_timer = threading.Timer(170, self.delayed_check)

        self.end_timer = threading.Timer(290, self.end_check)
        self.kill_pk_timer.start()
        self.end_timer.start()
        print(f"✅ PKBattleHandler 初始化，battle_type={self.battle_type}，定时器已启动")

    def update_battle_process(self, pk_battle_process_message):
        """更新最新的 PK_BATTLE_PROCESS_NEW 消息"""
        self.last_battle_process = pk_battle_process_message
        print("✅ 更新了 PK_BATTLE_PROCESS_NEW 数据")

    def update_info(self, pk_info_message):
        """更新 PK_INFO 消息"""
        self.last_pk_info = pk_info_message
        print("✅ 更新了 PK_INFO 数据")

    def delayed_check(self):
        """根据 PK 类型和票数触发绝杀计时器（kill_pk_timer）"""
        print("⏱️ 绝杀 PK 定时器触发")
        if self.pk_triggered:
            return

        try:
            if self.battle_type == 1 and self.last_battle_process:
                init_votes = self.last_battle_process["data"]["init_info"]["votes"]
                match_votes = self.last_battle_process["data"]["match_info"]["votes"]

                # 根据当前房间判断对比对象
                if self.room_id == self.last_battle_process["data"]["init_info"]["room_id"]:
                    self_votes = init_votes
                    opponent_votes = match_votes
                else:
                    self_votes = match_votes
                    opponent_votes = init_votes

                if self_votes == 0 and opponent_votes > 100:
                    print("❗ 对手 votes > 100 且本房间 votes == 0，触发 API")
                    self.pk_triggered = True
                    self.cancel_end_timer()
                    self.trigger_api()
                else:
                    print("✅ 绝杀条件不满足，不触发 API")
            elif self.battle_type == 2 and self.last_pk_info:
                members = self.last_pk_info["data"]["members"]
                self_participant = None
                opponent = None

                # 根据房间号区分参与者
                for member in members:
                    if member["room_id"] == self.room_id:
                        self_participant = member
                    else:
                        opponent = member

                if self_participant and opponent:
                    golds_self = self_participant.get("golds", 0)
                    votes_opponent = opponent.get("votes", 0)
                    if golds_self == 0 and votes_opponent > 100:
                        print("❗ 对手 votes > 100 且本房间 golds == 0，触发 API")
                        self.pk_triggered = True
                        self.cancel_end_timer()
                        self.trigger_api()
            else:
                print("❌ 缺少必要数据，无法进行票数对比")
        except Exception as e:
            print(f"❌ 绝杀检查出错: {e}")

    def end_check(self):
        """结束计时器逻辑"""
        print("⏱️ 结束计时器触发")
        if self.pk_triggered:
            return
        print("❗ 结束条件触发，直接调用 API")
        self.pk_triggered = True
        self.trigger_api()

    def cancel_end_timer(self):
        """取消结束计时器"""
        if self.end_timer:
            self.end_timer.cancel()
            print("✅ 已取消结束计时器")

    def stop(self):
        """销毁计时器"""
        if self.kill_pk_timer:
            self.kill_pk_timer.cancel()
        if self.end_timer:
            self.end_timer.cancel()
        print("🛑 停止计时器并销毁 PKBattleHandler 实例")

    def trigger_api(self):
        """触发 API"""
        post_url = f"{self.post_url}/pk_wanzun"
        
        # 设置默认空数据
        if self.battle_type == 1:
            pk_data = self.last_battle_process["data"] if self.last_battle_process else {}
        else:
            pk_data = self.last_pk_info["data"] if self.last_pk_info else {}

        payload = {
            "room_id": self.room_id,
            "battle_type": self.battle_type,
            "pk_data": pk_data,
            "token": "8096"
        }
        
        try:
            response = requests.post(post_url, json=payload, timeout=3)
            if response.status_code == 200:
                print(f"✅ PK API 已成功发送至 {post_url}")
            else:
                print(f"❌ PK API 发送失败，HTTP 状态码: {response.status_code}")
        except requests.RequestException as e:
            print(f"❌ PK API 发送异常: {e}")


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
                elif cmd == "PK_BATTLE_PROCESS_NEW":
                    if self.current_pk_handler:
                        self.current_pk_handler.update_battle_process(messages)
                elif cmd == "PK_BATTLE_START_NEW":
                    print("✅ 收到 PK_BATTLE_START_NEW 消息")
                    battle_type = messages["data"].get("battle_type", 1)
                    self.current_pk_handler = PKBattleHandler(
                        self.room_id, self.post_url, battle_type
                    )
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
