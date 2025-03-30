"""事件处理器基类模块

提供处理B站直播消息的基础抽象类
"""

from abc import ABC, abstractmethod
from typing import Dict, Any


class EventHandler(ABC):
    """事件处理器抽象基类
    
    所有具体的消息处理器都应该继承这个类并实现其抽象方法
    """
    
    @abstractmethod
    def handle(self, message: Dict[str, Any]) -> None:
        """处理事件消息
        
        Args:
            message: 待处理的消息数据
        """
        pass
    
    @abstractmethod
    def stop(self) -> None:
        """停止处理器
        
        用于资源清理和停止后台任务
        """
        pass 