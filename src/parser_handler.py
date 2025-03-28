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

        # PK类型日志记录
        print(f"🔄 PKBattleHandler 初始化，原始battle_type={battle_type}")
        
        # 将非类型1的所有PK归为类型2处理
        if self.battle_type != 1:
            print(f"📝 将battle_type从{self.battle_type}调整为2进行统一处理")
            self.battle_type = 2
        
        # 根据 battle_type 启动不同的计时器
        if self.battle_type == 1:
            self.kill_pk_timer = threading.Timer(170, self.delayed_check)
        else:
            self.kill_pk_timer = threading.Timer(170, self.delayed_check)

        self.end_timer = threading.Timer(290, self.end_check)
        self.kill_pk_timer.start()
        self.end_timer.start()
        print(f"✅ PKBattleHandler 初始化完成，battle_type={self.battle_type}，定时器已启动")

    def update_battle_process(self, pk_battle_process_message):
        """更新最新的 PK_BATTLE_PROCESS_NEW 消息"""
        self.last_battle_process = pk_battle_process_message
        
        # 添加更详细的日志记录
        try:
            if "data" in pk_battle_process_message and "init_info" in pk_battle_process_message["data"] and "match_info" in pk_battle_process_message["data"]:
                init_info = pk_battle_process_message["data"]["init_info"]
                match_info = pk_battle_process_message["data"]["match_info"]
                
                init_votes = init_info.get("votes", 0)
                match_votes = match_info.get("votes", 0)
                init_room_id = init_info.get("room_id", "未知")
                match_room_id = match_info.get("room_id", "未知")
                
                if self.room_id == init_room_id:
                    self_votes = init_votes
                    opponent_votes = match_votes
                    opponent_room_id = match_room_id
                else:
                    self_votes = match_votes
                    opponent_votes = init_votes
                    opponent_room_id = init_room_id
                
                print(f"📊 PK进程数据: 类型={self.battle_type}, 房间={self.room_id}, 己方票数={self_votes}, 对方房间={opponent_room_id}, 对方票数={opponent_votes}")
                
                # 打印所有可能的票数相关字段以便调试
                all_fields = []
                if "init_info" in pk_battle_process_message["data"]:
                    for key, value in pk_battle_process_message["data"]["init_info"].items():
                        if isinstance(value, (int, float)) or (isinstance(value, str) and value.isdigit()):
                            all_fields.append(f"init.{key}={value}")
                if "match_info" in pk_battle_process_message["data"]:
                    for key, value in pk_battle_process_message["data"]["match_info"].items():
                        if isinstance(value, (int, float)) or (isinstance(value, str) and value.isdigit()):
                            all_fields.append(f"match.{key}={value}")
                
                if all_fields:
                    print(f"🔢 数值字段: {', '.join(all_fields)}")
        except Exception as e:
            print(f"❌ 记录battle_process日志时出错: {e}")
            
        print("✅ 更新了 PK_BATTLE_PROCESS_NEW 数据")

    def update_info(self, pk_info_message):
        """更新 PK_INFO 消息"""
        self.last_pk_info = pk_info_message
        
        # 添加更详细的日志记录
        try:
            if "data" in pk_info_message and "members" in pk_info_message["data"]:
                members = pk_info_message["data"]["members"]
                self_participant = None
                opponent = None
                
                # 找出己方和对方
                for member in members:
                    if "room_id" in member and member["room_id"] == self.room_id:
                        self_participant = member
                    else:
                        opponent = member
                
                # 详细记录所有成员信息
                if members:
                    print(f"👥 PK总成员数: {len(members)}")
                    for i, member in enumerate(members):
                        room_id = member.get("room_id", "未知")
                        votes = member.get("votes", 0)
                        golds = member.get("golds", 0)
                        is_self = "✓" if room_id == self.room_id else "✗"
                        print(f"👤 成员{i+1}: 房间={room_id} {is_self}, 票数={votes}, 金币={golds}")
                
                # 汇总己方和对方的票数信息
                if self_participant and opponent:
                    votes_self = self_participant.get("votes", 0)
                    votes_opponent = opponent.get("votes", 0)
                    golds_self = self_participant.get("golds", 0)
                    golds_opponent = opponent.get("golds", 0)
                    opponent_room_id = opponent.get("room_id", "未知")
                    
                    print(f"📊 PK信息汇总: 类型={self.battle_type}, 房间={self.room_id}, 己方票数={votes_self}, 己方金币={golds_self}, 对方房间={opponent_room_id}, 对方票数={votes_opponent}, 对方金币={golds_opponent}")
                    
                    # 记录票数差距
                    votes_diff = votes_self - votes_opponent
                    if votes_diff > 0:
                        print(f"🥇 己方领先 {votes_diff} 票")
                    elif votes_diff < 0:
                        print(f"🥈 对方领先 {abs(votes_diff)} 票")
                    else:
                        print("🔄 双方票数持平")
                    
                    # 记录票数比例
                    total_votes = votes_self + votes_opponent
                    if total_votes > 0:
                        self_percentage = (votes_self / total_votes) * 100
                        opponent_percentage = (votes_opponent / total_votes) * 100
                        print(f"📈 票数比例: 己方 {self_percentage:.1f}%, 对方 {opponent_percentage:.1f}%")
                
                # 打印所有可能的票数相关字段以便调试
                if self_participant:
                    all_fields = []
                    for key, value in self_participant.items():
                        if isinstance(value, (int, float)) or (isinstance(value, str) and value.isdigit()):
                            all_fields.append(f"{key}={value}")
                    
                    if all_fields:
                        print(f"🔢 己方数值字段: {', '.join(all_fields)}")
        except Exception as e:
            print(f"❌ 记录pk_info日志时出错: {e}")
            
        print("✅ 更新了 PK_INFO 数据")

    def delayed_check(self):
        """根据 PK 类型和票数触发绝杀计时器（kill_pk_timer）"""
        print("⏱️ 绝杀 PK 定时器触发")
        if self.pk_triggered:
            print("❌ PK 已经被触发过，跳过检查")
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

                print(f"🔍 battle_type=1 检查: 房间={self.room_id}, 己方votes={self_votes}, 对方votes={opponent_votes}")
                
                if self_votes == 0 and opponent_votes > 100:
                    print("❗ 对手 votes > 100 且本房间 votes == 0，触发 API")
                    self.pk_triggered = True
                    self.cancel_end_timer()
                    self.trigger_api()
                else:
                    print(f"✅ 绝杀条件不满足，不触发 API: self_votes={self_votes}, opponent_votes={opponent_votes}")
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
                    votes_self = self_participant.get("votes", 0)
                    votes_opponent = opponent.get("votes", 0)
                    
                    print(f"🔍 battle_type=2 检查: 房间={self.room_id}, 己方golds={golds_self}, 己方votes={votes_self}, 对方votes={votes_opponent}")
                    
                    if votes_self == 0 and votes_opponent > 100:
                        print("❗ 对手 votes > 100 且本房间 votes == 0，触发 API")
                        self.pk_triggered = True
                        self.cancel_end_timer()
                        self.trigger_api()
                    else:
                        print(f"✅ 绝杀条件不满足，不触发 API: votes_self={votes_self}, votes_opponent={votes_opponent}")
                else:
                    print(f"❌ battle_type=2 找不到参与者信息")
            else:
                print(f"❌ 缺少必要数据，无法进行票数对比: battle_type={self.battle_type}, has_last_battle_process={self.last_battle_process is not None}, has_last_pk_info={self.last_pk_info is not None}")
        except Exception as e:
            print(f"❌ 绝杀检查出错: {e}")

    def end_check(self):
        """结束计时器逻辑"""
        print("⏱️ 结束计时器触发")
        if self.pk_triggered:
            print("❌ PK 已经被触发过，跳过结束检查")
            return
            
        try:
            should_trigger = False
            
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
                
                print(f"🔍 结束检查 battle_type=1: 己方votes={self_votes}, 对方votes={opponent_votes}")
                
                # 结束检查只需要己方票数为0，不需要检查对方票数
                if self_votes == 0:
                    should_trigger = True
                    print(f"⚠️ 结束检查：己方票数为0，将触发API")
                else:
                    print(f"✅ 结束检查：己方票数不为0 ({self_votes})，不触发API")
                
            elif self.battle_type == 2 and self.last_pk_info:
                members = self.last_pk_info["data"]["members"]
                self_participant = None
                opponent = None
                
                # 根据房间号找到己方参与者
                for member in members:
                    if member["room_id"] == self.room_id:
                        self_participant = member
                    else:
                        opponent = member
                
                if self_participant:
                    votes_self = self_participant.get("votes", 0)
                    votes_opponent = opponent.get("votes", 0) if opponent else -1
                    
                    print(f"🔍 结束检查 battle_type=2: 房间={self.room_id}, 己方votes={votes_self}, 对方votes={votes_opponent}")
                    
                    # 结束检查只需要己方票数为0，不需要检查对方票数
                    if votes_self == 0:
                        should_trigger = True
                        print(f"⚠️ 结束检查：己方票数为0，将触发API")
                    else:
                        print(f"✅ 结束检查：己方票数不为0 ({votes_self})，不触发API")
                else:
                    print(f"❌ battle_type=2 找不到己方参与者信息")
            else:
                print(f"❌ 结束检查：缺少必要数据，无法进行票数对比: battle_type={self.battle_type}, has_last_battle_process={self.last_battle_process is not None}, has_last_pk_info={self.last_pk_info is not None}")
            
            # 触发API如果应该触发
            if should_trigger:
                print("🚀 结束检查触发API")
                self.pk_triggered = True
                self.trigger_api()
                
        except Exception as e:
            print(f"❌ 结束检查出错: {e}")

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
    def __init__(self, room_id, spider=False):
        self.room_id = room_id
        self.post_url = "http://192.168.0.101:8081"
        self.current_pk_handler = None
        self.spider_enabled = spider
        
        if self.spider_enabled:
            print(f"🕷️ 直播间爬虫功能已启用，将监听 STOP_LIVE_ROOM_LIST 消息")

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
                elif cmd == "STOP_LIVE_ROOM_LIST" and self.spider_enabled:
                    print("📋 收到 STOP_LIVE_ROOM_LIST 消息")
                    self.handle_stop_live_room_list(messages)
                elif cmd == "SEND_GIFT":
                    print("🎁 收到 SEND_GIFT 消息")
                    self.handle_send_gift(messages)
        except Exception as e:
            print(f"❌ 处理消息时发生错误: {e}")

    def handle_stop_live_room_list(self, messages):
        """处理 STOP_LIVE_ROOM_LIST 消息并发送到指定 API"""
        post_url = f"{self.post_url}/live_room_spider"
        try:
            payload = {
                "room_id": self.room_id,
                "stop_live_room_list": messages.get("data", {})
            }
            
            response = requests.post(post_url, json=payload, timeout=3)
            if response.status_code == 200:
                print(f"✅ STOP_LIVE_ROOM_LIST 已成功发送至 {post_url}")
            else:
                print(f"❌ STOP_LIVE_ROOM_LIST 发送失败，HTTP 状态码: {response.status_code}")
        except requests.RequestException as e:
            print(f"❌ STOP_LIVE_ROOM_LIST 发送异常: {e}")

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
                
    def handle_send_gift(self, messages):
        """处理礼物消息并发送到指定 API"""
        try:
            data = messages.get("data", {})
            
            # 提取送礼信息
            uid = data.get("uid", 0)
            uname = data.get("uname", "")
            gift_id = data.get("giftId", 0)
            gift_name = data.get("giftName", "")
            price = data.get("price", 0)
            
            # 如果有 sender_uinfo 就从那里获取更详细的用户信息
            if "sender_uinfo" in data and "base" in data["sender_uinfo"]:
                sender_base = data["sender_uinfo"]["base"]
                uid = data["sender_uinfo"].get("uid", uid)
                uname = sender_base.get("name", uname)
            
            # 打印礼物信息
            print(f"🎁 礼物: [{uname}] 赠送 [{gift_name}] x1, 价值: {price}")
            
            # 发送到 /money 接口
            post_url = f"{self.post_url}/money"
            payload = {
                "room_id": self.room_id,
                "uid": uid,
                "uname": uname,
                "gift_id": gift_id,
                "gift_name": gift_name,
                "price": price
            }
            
            response = requests.post(post_url, json=payload, timeout=3)
            if response.status_code == 200:
                print(f"✅ 礼物信息已成功发送至 {post_url}")
            else:
                print(f"❌ 礼物信息发送失败，HTTP 状态码: {response.status_code}")
        except Exception as e:
            print(f"❌ 处理礼物消息时发生错误: {e}")
