"""消息处理器模块

各种B站直播消息的具体处理器实现
"""

import logging
import threading
from typing import Dict, Any, Optional, Type

from .handler_base import EventHandler
from .api_client import APIClient
from .constants import Constants
from .pk_data import PKDataCollector

logger = logging.getLogger(__name__)


class DanmakuHandler(EventHandler):
    """弹幕消息处理器"""
    
    def __init__(self, room_id: int, api_client: APIClient):
        """初始化弹幕处理器
        
        Args:
            room_id: 直播间ID
            api_client: API客户端
        """
        self.room_id = room_id
        self.api_client = api_client
    
    def handle(self, message: Dict[str, Any]) -> None:
        """处理弹幕消息
        
        Args:
            message: 弹幕消息数据
        """
        info = message.get("info", [])
        if len(info) > 2:
            comment = info[1]
            username = info[2][1]
            logger.info(f"[{username}] {comment}")
            
            # 关键词检测
            self._keyword_detection(comment, message)
            
            # 机器人指令检测
            if Constants.ROBOT_KEYWORD in comment:
                self._send_to_setting(comment, message)
    
    def _keyword_detection(self, danmaku: str, raw_message: Dict[str, Any]) -> None:
        """检测弹幕内容是否包含关键字并发送POST请求
        
        Args:
            danmaku: 弹幕内容
        """
        if any(keyword in danmaku for keyword in Constants.KEYWORDS):
            payload = {
                "room_id": self.room_id,
                "danmaku": danmaku,
                "raw_message": raw_message
            }
            if self.api_client.post(Constants.API_TICKET, payload):
                logger.info(f"✅ 关键字检测成功：'{danmaku}' 已发送")
    
    def _send_to_setting(self, danmaku: str, raw_message: Dict[str, Any]) -> None:
        """将包含"记仇机器人"的弹幕发送到/setting接口
        
        Args:
            danmaku: 弹幕内容
        """
        payload = {
            "room_id": self.room_id,
            "danmaku": danmaku,
            "raw_message": raw_message
        }
        if self.api_client.post(Constants.API_SETTING, payload):
            logger.info(f"✅ 记仇机器人指令：'{danmaku}' 已发送")
    
    def stop(self) -> None:
        """停止处理器"""
        pass


class GiftHandler(EventHandler):
    """礼物消息处理器"""
    
    def __init__(self, room_id: int, api_client: APIClient):
        """初始化礼物处理器
        
        Args:
            room_id: 直播间ID
            api_client: API客户端
        """
        self.room_id = room_id
        self.api_client = api_client
    
    def handle(self, message: Dict[str, Any]) -> None:
        """处理礼物消息
        
        Args:
            message: 礼物消息数据
        """
        try:
            data = message.get("data", {})
            
            # 提取送礼信息
            uid = data.get("uid", 0)
            uname = data.get("uname", "")
            gift_id = data.get("giftId", 0)
            gift_name = data.get("giftName", "")
            price = data.get("price", 0)
            
            # 如果有sender_uinfo就从那里获取更详细的用户信息
            if "sender_uinfo" in data and "base" in data["sender_uinfo"]:
                sender_base = data["sender_uinfo"]["base"]
                uid = data["sender_uinfo"].get("uid", uid)
                uname = sender_base.get("name", uname)
            
            # 打印礼物信息
            logger.info(f"🎁 礼物: [{uname}] 赠送 [{gift_name}] x1, 价值: {price}")
            
            # 发送到/money接口
            payload = {
                "room_id": self.room_id,
                "uid": uid,
                "uname": uname,
                "gift_id": gift_id,
                "gift_name": gift_name,
                "price": price
            }
            
            self.api_client.post(Constants.API_MONEY, payload)
        except Exception as e:
            logger.error(f"❌ 处理礼物消息时发生错误: {e}")
    
    def stop(self) -> None:
        """停止处理器"""
        pass


class LiveRoomListHandler(EventHandler):
    """直播间列表处理器"""
    
    def __init__(self, room_id: int, api_client: APIClient):
        """初始化直播间列表处理器
        
        Args:
            room_id: 直播间ID
            api_client: API客户端
        """
        self.room_id = room_id
        self.api_client = api_client
    
    def handle(self, message: Dict[str, Any]) -> None:
        """处理STOP_LIVE_ROOM_LIST消息
        
        Args:
            message: 直播间列表消息数据
        """
        payload = {
            "room_id": self.room_id,
            "stop_live_room_list": message.get("data", {})
        }
        
        if self.api_client.post(Constants.API_LIVE_ROOM_SPIDER, payload):
            logger.info("✅ STOP_LIVE_ROOM_LIST 已成功发送")
    
    def stop(self) -> None:
        """停止处理器"""
        pass


class PKBattleHandler(EventHandler):
    """PK战斗处理器"""
    
    def __init__(self, room_id: int, api_client: APIClient, battle_type: int):
        """初始化PK战斗处理器
        
        Args:
            room_id: 直播间ID
            api_client: API客户端
            battle_type: PK类型
        """
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
        """标准化PK类型，将非类型1的所有PK归为类型2处理
        
        Args:
            battle_type: 原始PK类型
            
        Returns:
            int: 标准化后的PK类型
        """
        logger.info(f"🔄 PKBattleHandler 初始化，原始battle_type={battle_type}")
        
        if battle_type != Constants.PK_TYPE_1:
            logger.info(f"📝 将battle_type从{battle_type}调整为{Constants.PK_TYPE_2}进行统一处理")
            return Constants.PK_TYPE_2
        return battle_type
    
    def handle(self, message: Dict[str, Any]) -> None:
        """处理PK消息
        
        Args:
            message: PK相关消息数据
        """
        cmd = message.get("cmd", "")
        
        if cmd == Constants.MSG_PK_INFO:
            self.data_collector.update_info(message)
        elif cmd == Constants.MSG_PK_PROCESS:
            self.data_collector.update_battle_process(message)
    
    def delayed_check(self) -> None:
        """根据PK类型和票数触发绝杀计时器"""
        logger.info("⏱️ 绝杀PK定时器触发")
        
        if self.pk_triggered:
            logger.info("❌ PK已经被触发过，跳过检查")
            return
        
        try:
            self_votes, opponent_votes = self.data_collector.get_votes_data(self.battle_type)
            
            logger.info(f"🔍 battle_type={self.battle_type} 检查: 房间={self.room_id}, 己方votes={self_votes}, 对方votes={opponent_votes}")
            
            if self_votes == 0 and opponent_votes > Constants.PK_OPPONENT_VOTES_THRESHOLD:
                logger.info(f"❗ 对手votes > {Constants.PK_OPPONENT_VOTES_THRESHOLD} 且本房间votes == 0，触发API")
                self.pk_triggered = True
                self.cancel_end_timer()
                self.trigger_api()
            else:
                logger.info(f"✅ 绝杀条件不满足，不触发API: self_votes={self_votes}, opponent_votes={opponent_votes}")
        except Exception as e:
            logger.error(f"❌ 绝杀检查出错: {e}")
    
    def end_check(self) -> None:
        """结束计时器逻辑"""
        logger.info("⏱️ 结束计时器触发")
        
        if self.pk_triggered:
            logger.info("❌ PK已经被触发过，跳过结束检查")
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
        logger.info("🛑 停止计时器并销毁PKBattleHandler实例")
    
    def trigger_api(self) -> None:
        """触发API"""
        pk_data = self.data_collector.get_pk_data(self.battle_type)
        
        payload = {
            "room_id": self.room_id,
            "battle_type": self.battle_type,
            "pk_data": pk_data,
            "token": Constants.DEFAULT_API_TOKEN
        }
        
        self.api_client.post(Constants.API_PK, payload)


class MessageHandlerFactory:
    """消息处理器工厂"""
    
    # 处理器映射
    _handlers: Dict[str, Type[EventHandler]] = {
        Constants.MSG_DANMU: DanmakuHandler,
        Constants.MSG_GIFT: GiftHandler,
        Constants.MSG_LIVE_ROOM_LIST: LiveRoomListHandler
    }
    
    @classmethod
    def register_handler(cls, cmd: str, handler_class: Type[EventHandler]) -> None:
        """注册新的处理器
        
        Args:
            cmd: 消息命令类型
            handler_class: 处理器类
        """
        cls._handlers[cmd] = handler_class
    
    @classmethod
    def create_handler(cls, cmd: str, room_id: int, api_client: APIClient) -> Optional[EventHandler]:
        """根据命令类型创建对应的处理器
        
        Args:
            cmd: 消息命令类型
            room_id: 直播间ID
            api_client: API客户端
            
        Returns:
            EventHandler或None: 创建的处理器实例，如果没有对应的处理器则返回None
        """
        handler_class = cls._handlers.get(cmd)
        if handler_class:
            return handler_class(room_id, api_client)
        return None 