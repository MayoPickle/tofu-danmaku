import json
import zlib
import brotli
import requests
import threading
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Callable, Union
from dataclasses import dataclass


# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# 常量定义
class Constants:
    DEFAULT_TIMEOUT = 3
    DEFAULT_API_TOKEN = "8096"
    KEYWORDS = ["观测站"]
    ROBOT_KEYWORD = "记仇机器人"
    CHATBOT_KEYWORDS = ["鱼豆腐", "豆豆"]  # 改为列表，包含多个关键词
    BLOCKED_USERNAME_PREFIXES = ["观"]  # 被屏蔽的用户名前缀列表
    
    # PK 相关常量
    PK_TYPE_1 = 1
    PK_TYPE_2 = 2
    PK_DELAYED_CHECK_TIME = 170  # 秒
    PK_END_CHECK_TIME = 290  # 秒
    PK_OPPONENT_VOTES_THRESHOLD = 100


# API 客户端
class APIClient:
    def __init__(self, base_url: str):
        self.base_url = base_url

    def post(self, endpoint: str, payload: Dict[str, Any]) -> tuple:
        """发送 POST 请求到指定端点
        
        Returns:
            tuple: (成功标志, 状态码或None)
        """
        url = f"{self.base_url}/{endpoint}"
        try:
            response = requests.post(url, json=payload, timeout=Constants.DEFAULT_TIMEOUT)
            status_code = response.status_code
            if status_code == 200:
                logger.info(f"✅ 请求成功发送至 {url}")
                return True, status_code
            else:
                logger.error(f"❌ 请求失败，HTTP 状态码: {status_code}")
                return False, status_code
        except requests.RequestException as e:
            logger.error(f"❌ 请求异常: {e}")
            return False, None


# 事件处理器基类
class EventHandler(ABC):
    @abstractmethod
    def handle(self, message: Dict[str, Any]) -> None:
        """处理事件消息"""
        pass
    
    @abstractmethod
    def stop(self) -> None:
        """停止处理器"""
        pass


# PK 数据收集器
class PKDataCollector:
    def __init__(self, room_id: int):
        self.room_id = room_id
        self.last_pk_info = None
        self.last_battle_process = None
    
    def update_battle_process(self, message: Dict[str, Any]) -> None:
        """更新 PK_BATTLE_PROCESS_NEW 消息数据"""
        self.last_battle_process = message
        self._log_battle_process_data(message)
    
    def update_info(self, message: Dict[str, Any]) -> None:
        """更新 PK_INFO 消息数据"""
        self.last_pk_info = message
        self._log_pk_info_data(message)
    
    def get_pk_data(self, battle_type: int) -> Dict[str, Any]:
        """根据 PK 类型获取相应数据"""
        if battle_type == Constants.PK_TYPE_1:
            return self.last_battle_process.get("data", {}) if self.last_battle_process else {}
        else:
            return self.last_pk_info.get("data", {}) if self.last_pk_info else {}
    
    def get_votes_data(self, battle_type: int) -> tuple:
        """获取己方和对方的票数数据"""
        self_votes = 0
        opponent_votes = 0
        
        try:
            if battle_type == Constants.PK_TYPE_1 and self.last_battle_process:
                data = self.last_battle_process.get("data", {})
                init_info = data.get("init_info", {})
                match_info = data.get("match_info", {})
                
                init_votes = init_info.get("votes", 0)
                match_votes = match_info.get("votes", 0)
                init_room_id = init_info.get("room_id", None)
                
                if self.room_id == init_room_id:
                    self_votes = init_votes
                    opponent_votes = match_votes
                else:
                    self_votes = match_votes
                    opponent_votes = init_votes
                    
            elif battle_type == Constants.PK_TYPE_2 and self.last_pk_info:
                members = self.last_pk_info.get("data", {}).get("members", [])
                self_participant = None
                opponent = None
                
                for member in members:
                    if member.get("room_id") == self.room_id:
                        self_participant = member
                    else:
                        opponent = member
                
                if self_participant and opponent:
                    self_votes = self_participant.get("votes", 0)
                    opponent_votes = opponent.get("votes", 0)
        except Exception as e:
            logger.error(f"❌ 获取票数数据时出错: {e}")
        
        return self_votes, opponent_votes
    
    def _log_battle_process_data(self, message: Dict[str, Any]) -> None:
        """记录 PK_BATTLE_PROCESS_NEW 消息的详细信息"""
        try:
            if "data" in message and "init_info" in message["data"] and "match_info" in message["data"]:
                init_info = message["data"]["init_info"]
                match_info = message["data"]["match_info"]
                
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
                
                logger.info(f"📊 PK进程数据: 房间={self.room_id}, 己方票数={self_votes}, 对方房间={opponent_room_id}, 对方票数={opponent_votes}")
                
                # 打印所有可能的票数相关字段以便调试
                all_fields = []
                for source, prefix in [(init_info, "init"), (match_info, "match")]:
                    for key, value in source.items():
                        if isinstance(value, (int, float)) or (isinstance(value, str) and value.isdigit()):
                            all_fields.append(f"{prefix}.{key}={value}")
                
                if all_fields:
                    logger.debug(f"🔢 数值字段: {', '.join(all_fields)}")
        except Exception as e:
            logger.error(f"❌ 记录battle_process日志时出错: {e}")
        
        logger.info("✅ 更新了 PK_BATTLE_PROCESS_NEW 数据")
    
    def _log_pk_info_data(self, message: Dict[str, Any]) -> None:
        """记录 PK_INFO 消息的详细信息"""
        try:
            if "data" in message and "members" in message["data"]:
                members = message["data"]["members"]
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
                    logger.info(f"👥 PK总成员数: {len(members)}")
                    for i, member in enumerate(members):
                        room_id = member.get("room_id", "未知")
                        votes = member.get("votes", 0)
                        golds = member.get("golds", 0)
                        is_self = "✓" if room_id == self.room_id else "✗"
                        logger.debug(f"👤 成员{i+1}: 房间={room_id} {is_self}, 票数={votes}, 金币={golds}")
                
                # 汇总己方和对方的票数信息
                if self_participant and opponent:
                    votes_self = self_participant.get("votes", 0)
                    votes_opponent = opponent.get("votes", 0)
                    golds_self = self_participant.get("golds", 0)
                    golds_opponent = opponent.get("golds", 0)
                    opponent_room_id = opponent.get("room_id", "未知")
                    
                    logger.info(f"📊 PK信息汇总: 房间={self.room_id}, 己方票数={votes_self}, 己方金币={golds_self}, "
                               f"对方房间={opponent_room_id}, 对方票数={votes_opponent}, 对方金币={golds_opponent}")
                    
                    # 记录票数差距和比例
                    votes_diff = votes_self - votes_opponent
                    total_votes = votes_self + votes_opponent
                    
                    if votes_diff > 0:
                        logger.info(f"🥇 己方领先 {votes_diff} 票")
                    elif votes_diff < 0:
                        logger.info(f"🥈 对方领先 {abs(votes_diff)} 票")
                    else:
                        logger.info("🔄 双方票数持平")
                    
                    if total_votes > 0:
                        self_percentage = (votes_self / total_votes) * 100
                        opponent_percentage = (votes_opponent / total_votes) * 100
                        logger.info(f"📈 票数比例: 己方 {self_percentage:.1f}%, 对方 {opponent_percentage:.1f}%")
        except Exception as e:
            logger.error(f"❌ 记录pk_info日志时出错: {e}")
        
        logger.info("✅ 更新了 PK_INFO 数据")


# PK 战斗处理器
class PKBattleHandler(EventHandler):
    def __init__(self, room_id: int, api_client: APIClient, battle_type: int):
        self.room_id = room_id
        self.api_client = api_client
        self.battle_type = self._normalize_battle_type(battle_type)
        self.data_collector = PKDataCollector(room_id)
        self.pk_triggered = False
        
        # 初始化定时器
        self.delayed_check_timer = threading.Timer(Constants.PK_DELAYED_CHECK_TIME, self.delayed_check)
        self.end_timer = threading.Timer(Constants.PK_END_CHECK_TIME, self.end_check)
        
        # 启动定时器
        self.delayed_check_timer.start()
        self.end_timer.start()
        
        logger.info(f"✅ PKBattleHandler 初始化完成，battle_type={self.battle_type}，定时器已启动")
    
    def _normalize_battle_type(self, battle_type: int) -> int:
        """标准化 PK 类型，将非类型1的所有 PK 归为类型2处理"""
        logger.info(f"🔄 PKBattleHandler 初始化，原始battle_type={battle_type}")
        
        if battle_type != Constants.PK_TYPE_1:
            logger.info(f"📝 将battle_type从{battle_type}调整为{Constants.PK_TYPE_2}进行统一处理")
            return Constants.PK_TYPE_2
        return battle_type
    
    def handle(self, message: Dict[str, Any]) -> None:
        """处理 PK 消息"""
        cmd = message.get("cmd", "")
        
        if cmd == "PK_INFO":
            self.data_collector.update_info(message)
        elif cmd == "PK_BATTLE_PROCESS_NEW":
            self.data_collector.update_battle_process(message)
    
    def delayed_check(self) -> None:
        """根据 PK 类型和票数触发绝杀计时器"""
        logger.info("⏱️ 绝杀 PK 定时器触发")
        
        if self.pk_triggered:
            logger.info("❌ PK 已经被触发过，跳过检查")
            return
        
        try:
            self_votes, opponent_votes = self.data_collector.get_votes_data(self.battle_type)
            
            logger.info(f"🔍 battle_type={self.battle_type} 检查: 房间={self.room_id}, 己方votes={self_votes}, 对方votes={opponent_votes}")
            
            if self_votes == 0 and opponent_votes > Constants.PK_OPPONENT_VOTES_THRESHOLD:
                logger.info(f"❗ 对手 votes > {Constants.PK_OPPONENT_VOTES_THRESHOLD} 且本房间 votes == 0，触发 API")
                self.pk_triggered = True
                self.cancel_end_timer()
                self.trigger_api()
            else:
                logger.info(f"✅ 绝杀条件不满足，不触发 API: self_votes={self_votes}, opponent_votes={opponent_votes}")
        except Exception as e:
            logger.error(f"❌ 绝杀检查出错: {e}")
    
    def end_check(self) -> None:
        """结束计时器逻辑"""
        logger.info("⏱️ 结束计时器触发")
        
        if self.pk_triggered:
            logger.info("❌ PK 已经被触发过，跳过结束检查")
            return
        
        try:
            self_votes, _ = self.data_collector.get_votes_data(self.battle_type)
            
            logger.info(f"🔍 结束检查 battle_type={self.battle_type}: 己方votes={self_votes}")
            
            # 结束检查只需要己方票数为0，不需要检查对方票数
            if self_votes == 0:
                logger.info("⚠️ 结束检查：己方票数为0，将触发API")
                self.pk_triggered = True
                self.trigger_api()
            else:
                logger.info(f"✅ 结束检查：己方票数不为0 ({self_votes})，不触发API")
        except Exception as e:
            logger.error(f"❌ 结束检查出错: {e}")
    
    def cancel_end_timer(self) -> None:
        """取消结束计时器"""
        if self.end_timer:
            self.end_timer.cancel()
            logger.info("✅ 已取消结束计时器")
    
    def stop(self) -> None:
        """销毁计时器"""
        if self.delayed_check_timer:
            self.delayed_check_timer.cancel()
        if self.end_timer:
            self.end_timer.cancel()
        logger.info("🛑 停止计时器并销毁 PKBattleHandler 实例")
    
    def trigger_api(self) -> None:
        """触发 API"""
        pk_data = self.data_collector.get_pk_data(self.battle_type)
        
        payload = {
            "room_id": self.room_id,
            "battle_type": self.battle_type,
            "pk_data": pk_data,
            "token": Constants.DEFAULT_API_TOKEN
        }
        
        self.api_client.post("pk_wanzun", payload)


# 弹幕处理器
class DanmakuHandler(EventHandler):
    def __init__(self, room_id: int, api_client: APIClient):
        self.room_id = room_id
        self.api_client = api_client
    
    def handle(self, message: Dict[str, Any]) -> None:
        """处理弹幕消息"""
        info = message.get("info", [])
        if len(info) > 2:
            comment = info[1]
            username = info[2][1]
            logger.info(f"[{username}] {comment}")
            
            # 检查用户名是否以"观"开头，如果是则不处理
            if username.startswith("观"):
                logger.info(f"⛔ 忽略来自以'观'开头的用户的消息: [{username}] '{comment}'")
                return
            
            # 关键词检测
            self._keyword_detection(comment)
            
            # chatbot关键词检测和点赞检测
            if any(keyword in comment for keyword in Constants.CHATBOT_KEYWORDS):
                modified_comment = comment
                
                # 检查是否是豆豆+点赞组合，如果是则先处理sendlike
                if "豆豆" in comment and "点赞" in comment:
                    error_msg = self._sendlike_detection(comment)
                    if error_msg:
                        # 如果有错误信息，则将其附加到原始消息后
                        modified_comment = f"{comment} {error_msg}"
                
                # 然后再处理chatbot
                self._chatbot_detection(modified_comment)
            
            # 机器人指令检测
            if Constants.ROBOT_KEYWORD in comment:
                self._send_to_setting(comment)
    
    def _keyword_detection(self, danmaku: str) -> None:
        """检测弹幕内容是否包含关键字并发送 POST 请求"""
        if any(keyword in danmaku for keyword in Constants.KEYWORDS):
            payload = {
                "room_id": self.room_id,
                "danmaku": danmaku
            }
            success, _ = self.api_client.post("ticket", payload)
            if success:
                logger.info(f"✅ 关键字检测成功：'{danmaku}' 已发送至 ticket 接口")
    
    def _chatbot_detection(self, danmaku: str) -> None:
        """检测弹幕内容是否包含chatbot关键词并发送到 chatbot 接口"""
        # 记录触发的关键词
        triggered_keywords = [keyword for keyword in Constants.CHATBOT_KEYWORDS if keyword in danmaku]
        keywords_str = "、".join(triggered_keywords)
        
        logger.info(f"🤖 检测到chatbot关键词「{keywords_str}」：'{danmaku}'")
        
        chatbot_payload = {
            "room_id": str(self.room_id),
            "message": danmaku
        }
        success, _ = self.api_client.post("chatbot", chatbot_payload)
        if success:
            logger.info(f"✅ 已将消息 '{danmaku}' 发送到 chatbot 接口")
        else:
            logger.error(f"❌ 消息 '{danmaku}' 发送到 chatbot 接口失败")
    
    def _sendlike_detection(self, danmaku: str) -> Optional[str]:
        """发送包含豆豆和点赞的消息到 sendlike 接口
        
        Returns:
            Optional[str]: 如果发生错误，返回错误信息；如果成功，返回None
        """
        logger.info(f"👍 检测到豆豆+点赞组合：'{danmaku}'")
        
        sendlike_payload = {
            "room_id": str(self.room_id),
            "message": danmaku
        }
        success, status_code = self.api_client.post("sendlike", sendlike_payload)
        
        if success:
            logger.info(f"✅ 已将消息 '{danmaku}' 发送到 sendlike 接口")
            return None
        else:
            error_msg = f"（已触发点赞服务，但服务器返回{status_code or '未知错误'}）"
            logger.error(f"❌ 消息 '{danmaku}' 发送到 sendlike 接口失败: {status_code}")
            return error_msg
    
    def _send_to_setting(self, danmaku: str) -> None:
        """将包含"记仇机器人"的弹幕发送到 /setting 接口"""
        payload = {
            "room_id": self.room_id,
            "danmaku": danmaku
        }
        success, _ = self.api_client.post("setting", payload)
        if success:
            logger.info(f"✅ 记仇机器人指令：'{danmaku}' 已发送")
    
    def stop(self) -> None:
        """停止处理器"""
        pass


# 礼物处理器
class GiftHandler(EventHandler):
    def __init__(self, room_id: int, api_client: APIClient):
        self.room_id = room_id
        self.api_client = api_client
    
    def handle(self, message: Dict[str, Any]) -> None:
        """处理礼物消息"""
        try:
            data = message.get("data", {})
            
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
            logger.info(f"🎁 礼物: [{uname}] 赠送 [{gift_name}] x1, 价值: {price}")
            
            # 发送到 /money 接口
            payload = {
                "room_id": self.room_id,
                "uid": uid,
                "uname": uname,
                "gift_id": gift_id,
                "gift_name": gift_name,
                "price": price
            }
            
            self.api_client.post("money", payload)
        except Exception as e:
            logger.error(f"❌ 处理礼物消息时发生错误: {e}")
    
    def stop(self) -> None:
        """停止处理器"""
        pass


# 直播间列表处理器
class LiveRoomListHandler(EventHandler):
    def __init__(self, room_id: int, api_client: APIClient):
        self.room_id = room_id
        self.api_client = api_client
    
    def handle(self, message: Dict[str, Any]) -> None:
        """处理 STOP_LIVE_ROOM_LIST 消息"""
        payload = {
            "room_id": self.room_id,
            "stop_live_room_list": message.get("data", {})
        }
        
        if self.api_client.post("live_room_spider", payload):
            logger.info("✅ STOP_LIVE_ROOM_LIST 已成功发送")
    
    def stop(self) -> None:
        """停止处理器"""
        pass


# 消息处理工厂
class MessageHandlerFactory:
    @staticmethod
    def create_handler(cmd: str, room_id: int, api_client: APIClient, spider_enabled: bool = False) -> Optional[EventHandler]:
        """根据命令类型创建对应的处理器
        
        Args:
            cmd: 消息命令
            room_id: 房间ID
            api_client: API客户端
            spider_enabled: 是否启用爬虫功能
            
        Returns:
            EventHandler或None: 创建的处理器实例
        """
        # 如果是STOP_LIVE_ROOM_LIST消息但爬虫功能未启用，则不创建处理器
        if cmd == "STOP_LIVE_ROOM_LIST" and not spider_enabled:
            return None
            
        handlers = {
            "DANMU_MSG": DanmakuHandler,
            "SEND_GIFT": GiftHandler,
            "STOP_LIVE_ROOM_LIST": LiveRoomListHandler
        }
        
        handler_class = handlers.get(cmd)
        if handler_class:
            return handler_class(room_id, api_client)
        return None


# B站消息解析器
class BiliMessageParser:
    def __init__(self, room_id: int, api_base_url: str = "http://192.168.0.101:8081", spider: bool = False):
        self.room_id = room_id
        self.api_client = APIClient(api_base_url)
        self.current_pk_handler = None
        # 确保将spider参数转换为布尔值
        self.spider_enabled = bool(spider)
        
        # 初始化处理器映射
        self.persistent_handlers = {}
        
        # 注册处理器
        if self.spider_enabled:
            self.persistent_handlers["STOP_LIVE_ROOM_LIST"] = LiveRoomListHandler(room_id, self.api_client)
            logger.info("🕷️ 直播间爬虫功能已启用，将监听 STOP_LIVE_ROOM_LIST 消息")
        else:
            logger.info("ℹ️ 直播间爬虫功能未启用")
    
    def parse_message(self, data: bytes) -> None:
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
                        message = json.loads(body.decode("utf-8"))
                        self._handle_message(message)
                    elif operation == 3:
                        popularity = int.from_bytes(body, "big")
                offset += packet_length
        except Exception as e:
            logger.error(f"❌ 消息解析错误: {e}")
    
    def _handle_message(self, message: Dict[str, Any]) -> None:
        """处理解析后的消息"""
        try:
            if isinstance(message, dict):
                cmd = message.get("cmd", "")
                
                # 处理 PK 相关消息
                if cmd == "PK_INFO" or cmd == "PK_BATTLE_PROCESS_NEW":
                    if self.current_pk_handler:
                        self.current_pk_handler.handle(message)
                elif cmd == "PK_BATTLE_START_NEW":
                    logger.info("✅ 收到 PK_BATTLE_START_NEW 消息")
                    battle_type = message["data"].get("battle_type", Constants.PK_TYPE_1)
                    self.current_pk_handler = PKBattleHandler(
                        self.room_id, self.api_client, battle_type
                    )
                elif cmd == "PK_BATTLE_END":
                    logger.info("🛑 收到 PK_BATTLE_END 消息，销毁 PKBattleHandler 实例")
                    if self.current_pk_handler:
                        self.current_pk_handler.stop()
                        self.current_pk_handler = None
                # 对STOP_LIVE_ROOM_LIST消息的特殊处理: 只有当spider_enabled为真时才处理
                elif cmd == "STOP_LIVE_ROOM_LIST":
                    if self.spider_enabled:
                        handler = self.persistent_handlers.get(cmd)
                        if handler:
                            handler.handle(message)
                    else:
                        logger.debug(f"收到STOP_LIVE_ROOM_LIST消息，但爬虫功能未启用，忽略此消息")
                # 处理其他消息
                else:
                    # 检查是否有持久化处理器
                    handler = self.persistent_handlers.get(cmd)
                    
                    # 如果没有持久化处理器，则创建一个临时处理器
                    if not handler and cmd != "":
                        handler = MessageHandlerFactory.create_handler(cmd, self.room_id, self.api_client, self.spider_enabled)
                    
                    # 如果有处理器，则处理消息
                    if handler:
                        handler.handle(message)
        except Exception as e:
            logger.error(f"❌ 处理消息时发生错误: {e}")
