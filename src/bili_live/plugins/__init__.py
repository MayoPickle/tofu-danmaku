"""B站直播消息处理插件包

提供可扩展的插件系统，用于处理B站直播间各类消息和事件
"""

from .keyword_plugin import KeywordPlugin

__all__ = [
    'KeywordPlugin',
] 