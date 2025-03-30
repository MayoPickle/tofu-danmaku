"""B站消息解析器模块

负责解析B站直播协议消息并分发给对应的处理器
"""

import json
import zlib
import brotli
import logging
from typing import Dict, Any, Optional

from .constants import Constants
from .api_client import APIClient
from .handler_base import EventHandler
from .handlers import MessageHandlerFactory, PKBattleHandler, LiveRoomListHandler

logger = logging.getLogger(__name__)


class BiliMessageParser:
    """B站消息解析器
    
    解析B站直播WebSocket消息并分发给对应的处理器
    """
    
    def __init__(self, room_id: int, api_base_url: str = Constants.DEFAULT_API_URL, spider: bool = False):
        """初始化B站消息解析器
        
        Args:
            room_id: 直播间ID
            api_base_url: API服务器的基础URL
            spider: 是否启用爬虫功能
        """
        self.room_id = room_id
        self.api_client = APIClient(api_base_url)
        self.current_pk_handler = None
        self.spider_enabled = bool(spider)  # 确保转换为布尔值
        
        # 初始化处理器映射
        self.persistent_handlers = {}
        
        # 注册处理器
        if self.spider_enabled:
            self.persistent_handlers[Constants.MSG_LIVE_ROOM_LIST] = LiveRoomListHandler(room_id, self.api_client)
            logger.info("🕷️ 直播间爬虫功能已启用，将监听 STOP_LIVE_ROOM_LIST 消息")
        else:
            logger.info("ℹ️ 直播间爬虫功能未启用")
    
    def parse_message(self, data: bytes) -> None:
        """解析服务器返回的消息
        
        Args:
            data: 原始二进制消息数据
        """
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
                        logger.debug(f"直播间人气值: {popularity}")
                offset += packet_length
        except Exception as e:
            logger.error(f"❌ 消息解析错误: {e}")
    
    def _handle_message(self, message: Dict[str, Any]) -> None:
        """处理解析后的消息
        
        Args:
            message: 解析后的消息数据
        """
        try:
            if isinstance(message, dict):
                cmd = message.get("cmd", "")
                
                # 处理PK相关消息
                if cmd in (Constants.MSG_PK_INFO, Constants.MSG_PK_PROCESS):
                    if self.current_pk_handler:
                        self.current_pk_handler.handle(message)
                elif cmd == Constants.MSG_PK_START:
                    logger.info("✅ 收到 PK_BATTLE_START_NEW 消息")
                    battle_type = message["data"].get("battle_type", Constants.PK_TYPE_1)
                    self.current_pk_handler = PKBattleHandler(
                        self.room_id, self.api_client, battle_type
                    )
                elif cmd == Constants.MSG_PK_END:
                    logger.info("🛑 收到 PK_BATTLE_END 消息，销毁 PKBattleHandler 实例")
                    if self.current_pk_handler:
                        self.current_pk_handler.stop()
                        self.current_pk_handler = None
                # 处理其他消息
                else:
                    # 检查是否有持久化处理器
                    handler = self.persistent_handlers.get(cmd)
                    
                    # 如果没有持久化处理器，则创建一个临时处理器
                    if not handler and cmd != "":
                        handler = MessageHandlerFactory.create_handler(cmd, self.room_id, self.api_client)
                    
                    # 如果有处理器，则处理消息
                    if handler:
                        handler.handle(message)
        except Exception as e:
            logger.error(f"❌ 处理消息时发生错误: {e}") 