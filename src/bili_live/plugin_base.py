"""插件系统基类模块

定义插件系统的基础接口和框架
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class PluginBase(ABC):
    """插件基类
    
    所有插件都应该继承此类并实现其抽象方法
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """插件名称"""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """插件描述"""
        pass
    
    @property
    def version(self) -> str:
        """插件版本"""
        return "1.0.0"
    
    @property
    def enabled(self) -> bool:
        """插件是否启用"""
        return self._enabled
    
    @enabled.setter
    def enabled(self, value: bool) -> None:
        """设置插件启用状态"""
        self._enabled = value
    
    def __init__(self) -> None:
        """初始化插件"""
        self._enabled = True
        logger.info(f"插件 {self.name} v{self.version} 已加载")
    
    @abstractmethod
    def on_load(self) -> None:
        """插件加载时调用"""
        pass
    
    @abstractmethod
    def on_unload(self) -> None:
        """插件卸载时调用"""
        pass
    
    @abstractmethod
    def on_message(self, message: Dict[str, Any]) -> bool:
        """处理消息
        
        Args:
            message: 消息数据
            
        Returns:
            bool: 是否继续传递消息给其他插件
        """
        pass


class PluginManager:
    """插件管理器
    
    负责加载、启用、禁用和卸载插件
    """
    
    def __init__(self):
        """初始化插件管理器"""
        self.plugins: List[PluginBase] = []
    
    def register_plugin(self, plugin: PluginBase) -> None:
        """注册插件
        
        Args:
            plugin: 要注册的插件实例
        """
        self.plugins.append(plugin)
        plugin.on_load()
        logger.info(f"插件 {plugin.name} 已注册")
    
    def unregister_plugin(self, plugin_name: str) -> bool:
        """注销插件
        
        Args:
            plugin_name: 要注销的插件名称
            
        Returns:
            bool: 是否成功注销
        """
        for i, plugin in enumerate(self.plugins):
            if plugin.name == plugin_name:
                plugin.on_unload()
                self.plugins.pop(i)
                logger.info(f"插件 {plugin_name} 已注销")
                return True
        return False
    
    def enable_plugin(self, plugin_name: str) -> bool:
        """启用插件
        
        Args:
            plugin_name: 要启用的插件名称
            
        Returns:
            bool: 是否成功启用
        """
        for plugin in self.plugins:
            if plugin.name == plugin_name:
                plugin.enabled = True
                logger.info(f"插件 {plugin_name} 已启用")
                return True
        return False
    
    def disable_plugin(self, plugin_name: str) -> bool:
        """禁用插件
        
        Args:
            plugin_name: 要禁用的插件名称
            
        Returns:
            bool: 是否成功禁用
        """
        for plugin in self.plugins:
            if plugin.name == plugin_name:
                plugin.enabled = False
                logger.info(f"插件 {plugin_name} 已禁用")
                return True
        return False
    
    def process_message(self, message: Dict[str, Any]) -> None:
        """处理消息，传递给所有启用的插件
        
        Args:
            message: 消息数据
        """
        for plugin in self.plugins:
            if plugin.enabled:
                try:
                    # 如果插件返回False，不再继续传递消息
                    if not plugin.on_message(message):
                        break
                except Exception as e:
                    logger.error(f"插件 {plugin.name} 处理消息时出错: {e}")
    
    def get_plugin(self, plugin_name: str) -> Optional[PluginBase]:
        """获取插件实例
        
        Args:
            plugin_name: 插件名称
            
        Returns:
            Optional[PluginBase]: 插件实例，如果不存在则返回None
        """
        for plugin in self.plugins:
            if plugin.name == plugin_name:
                return plugin
        return None
    
    def get_all_plugins(self) -> List[Dict[str, Any]]:
        """获取所有插件的信息
        
        Returns:
            List[Dict[str, Any]]: 插件信息列表
        """
        return [
            {
                "name": plugin.name,
                "description": plugin.description,
                "version": plugin.version,
                "enabled": plugin.enabled
            }
            for plugin in self.plugins
        ] 