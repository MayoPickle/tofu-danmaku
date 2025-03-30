"""关键词插件

检测直播弹幕中的特定关键词并触发对应操作
"""

import logging
from typing import Dict, Any, List, Set

from ..constants import Constants
from ..api_client import APIClient
from ..plugin_base import PluginBase

logger = logging.getLogger(__name__)


class KeywordPlugin(PluginBase):
    """关键词检测插件"""
    
    @property
    def name(self) -> str:
        return "keyword_detector"
    
    @property
    def description(self) -> str:
        return "检测直播弹幕中的特定关键词并触发对应操作"
    
    @property
    def version(self) -> str:
        return "1.0.0"
    
    def __init__(self, room_id: int, api_client: APIClient, keywords: List[str] = None) -> None:
        """初始化关键词插件
        
        Args:
            room_id: 直播间ID
            api_client: API客户端
            keywords: 要检测的关键词列表，为None则使用默认关键词
        """
        super().__init__()
        self.room_id = room_id
        self.api_client = api_client
        self.keywords: Set[str] = set(keywords or Constants.KEYWORDS)
        logger.info(f"关键词插件初始化完成，监控关键词: {', '.join(self.keywords)}")
    
    def on_load(self) -> None:
        """插件加载时调用"""
        logger.info("关键词插件已加载")
    
    def on_unload(self) -> None:
        """插件卸载时调用"""
        logger.info("关键词插件已卸载")
    
    def on_message(self, message: Dict[str, Any]) -> bool:
        """处理消息
        
        Args:
            message: 消息数据
            
        Returns:
            bool: 是否继续传递消息给其他插件
        """
        # 只处理弹幕消息
        if message.get("cmd") != Constants.MSG_DANMU:
            return True
        
        try:
            info = message.get("info", [])
            if len(info) > 2:
                comment = info[1]
                username = info[2][1]
                
                # 检查是否包含关键词
                matched_keywords = [kw for kw in self.keywords if kw in comment]
                if matched_keywords:
                    logger.info(f"检测到关键词 {matched_keywords} 在用户 {username} 的弹幕中: {comment}")
                    self._handle_keyword_match(comment, matched_keywords)
        except Exception as e:
            logger.error(f"处理关键词时出错: {e}")
        
        # 继续传递消息给其他插件
        return True
    
    def _handle_keyword_match(self, danmaku: str, matched_keywords: List[str]) -> None:
        """处理关键词匹配
        
        Args:
            danmaku: 弹幕内容
            matched_keywords: 匹配到的关键词列表
        """
        # 发送到票务接口
        payload = {
            "room_id": self.room_id,
            "danmaku": danmaku,
            "keywords": matched_keywords
        }
        
        if self.api_client.post(Constants.API_TICKET, payload):
            logger.info(f"✅ 关键词匹配成功通知已发送")
    
    def add_keyword(self, keyword: str) -> None:
        """添加关键词
        
        Args:
            keyword: 要添加的关键词
        """
        self.keywords.add(keyword)
        logger.info(f"添加关键词: {keyword}")
    
    def remove_keyword(self, keyword: str) -> bool:
        """移除关键词
        
        Args:
            keyword: 要移除的关键词
            
        Returns:
            bool: 是否成功移除
        """
        if keyword in self.keywords:
            self.keywords.remove(keyword)
            logger.info(f"移除关键词: {keyword}")
            return True
        return False
    
    def get_keywords(self) -> List[str]:
        """获取当前所有关键词
        
        Returns:
            List[str]: 关键词列表
        """
        return list(self.keywords) 