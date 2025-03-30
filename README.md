# B站直播消息处理系统

这是一个用于处理B站直播间各类消息的模块化系统，支持弹幕、礼物、PK等消息的处理和转发。

## 特性

- 模块化设计，各组件职责明确
- 完善的日志系统
- 可扩展的插件架构
- 强类型提示，代码易读易维护
- 统一的API通信接口

## 项目结构

```
src/
  ├── bili_live/           # 核心包
  │   ├── __init__.py      # 包初始化文件
  │   ├── api_client.py    # API客户端
  │   ├── constants.py     # 常量定义
  │   ├── handler_base.py  # 事件处理器基类
  │   ├── handlers.py      # 各类消息处理器
  │   ├── logger.py        # 日志系统
  │   ├── parser.py        # 消息解析器
  │   ├── pk_data.py       # PK数据处理
  │   ├── plugin_base.py   # 插件系统基类
  │   └── plugins/         # 插件目录
  │       ├── __init__.py
  │       └── keyword_plugin.py   # 关键词插件
  ├── parser_handler.py    # 旧版入口文件
  └── parser_handler_v2.py # 新版入口文件
```

## 使用方法

### 基本用法

```python
from bili_live.parser import BiliMessageParser
from bili_live.logger import setup_logger

# 设置日志
logger = setup_logger("bili_live", level=logging.INFO)

# 创建解析器
parser = BiliMessageParser(room_id=12345)

# 假设你从WebSocket中获取到了消息数据
# data = websocket.receive()

# 解析消息
parser.parse_message(data)
```

### 插件系统

```python
from bili_live.parser import BiliMessageParser
from bili_live.api_client import APIClient
from bili_live.plugins.keyword_plugin import KeywordPlugin
from bili_live.plugin_base import PluginManager

# 创建API客户端
api_client = APIClient("http://api.example.com")

# 创建插件管理器
plugin_manager = PluginManager()

# 创建并注册关键词插件
keyword_plugin = KeywordPlugin(room_id=12345, api_client=api_client, 
                              keywords=["观测站", "鱼豆腐", "新关键词"])
plugin_manager.register_plugin(keyword_plugin)

# 处理消息
def handle_message(data):
    # 解析原始数据
    # ...
    
    # 将解析后的消息传递给插件系统
    plugin_manager.process_message(message)
```

## 自定义插件

创建自己的插件非常简单，只需继承`PluginBase`类并实现必要的方法：

```python
from bili_live.plugin_base import PluginBase

class MyPlugin(PluginBase):
    @property
    def name(self) -> str:
        return "my_plugin"
    
    @property
    def description(self) -> str:
        return "这是我的自定义插件"
    
    def on_load(self) -> None:
        print("插件已加载")
    
    def on_unload(self) -> None:
        print("插件已卸载")
    
    def on_message(self, message: dict) -> bool:
        # 处理消息
        print(f"收到消息: {message}")
        return True  # 继续传递消息给其他插件
```

## 贡献

欢迎提交Issue和Pull Request！
