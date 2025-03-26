# Tofu-Danmaku 豆腐弹幕姬

[English](#english) | [中文](#chinese)

---

<a name="english"></a>
# Tofu-Danmaku

A Python-based Bilibili (哔哩哔哩) live streaming danmaku (弹幕) client that allows you to connect to live streaming rooms and receive real-time chat messages.

## Features

- Connect to Bilibili live streaming rooms using room ID
- Display real-time danmaku messages
- Save and manage room history with custom notes
- Command history support for easy room navigation
- Optional spider mode for monitoring STOP_LIVE_ROOM_LIST messages
- Command-line interface with argument support
- Docker support for containerized deployment
- Cross-platform compatibility (Windows, macOS, Linux)
- Advanced PK battle monitoring and analysis
- Keyword detection system
- WebSocket-based real-time communication
- Automatic heartbeat management

## Requirements

- Python 3.x
- brotli
- websocket-client
- requests

## Installation

### Method 1: Direct Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/Tofu-Danmaku.git
cd Tofu-Danmaku
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

### Method 2: Using Docker

1. Build the Docker image:
```bash
docker build -t tofu-danmaku .
```

2. Run the container:
```bash
docker run -it tofu-danmaku
```

## Technical Details

### Core Components

1. **BiliDanmakuClient (`bili_danmaku_client.py`)**
   - Main WebSocket client implementation
   - Handles connection management
   - Implements automatic heartbeat mechanism
   - Manages authentication and server communication

2. **Message Parser (`parser_handler.py`)**
   - Processes incoming WebSocket messages
   - Handles different message types:
     - Danmaku messages
     - PK battle information
     - Room status updates
   - Implements keyword detection
   - Manages PK battle monitoring

3. **Room History Manager (`room_history.py`)**
   - Maintains connection history
   - Manages room notes and metadata
   - Provides history navigation

4. **Network Components**
   - `fetch.py`: Handles server info retrieval
   - `packet.py`: Manages WebSocket packet creation

### Message Types

The client handles several types of messages:

1. **Danmaku Messages**
   - Regular chat messages
   - Special commands
   - System notifications

2. **PK Battle Information**
   - Battle progress updates
   - Vote counts
   - Gold counts
   - Battle status changes

3. **Room Status Updates**
   - Live status changes
   - Room configuration updates
   - Viewer count updates

## Advanced Usage

### PK Battle Monitoring

The system supports two types of PK battles:

1. **Type 1 PK Battles**
```python
python main.py --room-id <ROOM_ID> --spider
```
- Monitors initial battle setup
- Tracks vote counts
- Analyzes battle progress
- Triggers alerts based on conditions

2. **Type 2 PK Battles**
- Monitors extended battle information
- Tracks both votes and gold counts
- Provides detailed battle analytics

### Keyword Detection

The system monitors messages for specific keywords:
- Default keywords: "观测站", "鱼豆腐"
- Customizable through code modification
- Real-time notification on keyword matches

### Spider Mode Features

When spider mode is enabled:
1. Monitors STOP_LIVE_ROOM_LIST messages
2. Tracks room status changes
3. Provides extended data collection
4. Enables advanced analytics

## Monitoring and Debugging

### Log Messages

The system uses different emoji indicators for log messages:
- ✅ Success messages
- ❌ Error messages
- 📊 Statistics and data
- 🔄 Process updates
- ⏱️ Timer events
- 🔍 Inspection results

### Common Debug Points

1. **Connection Issues**
```python
# Check WebSocket connection
ws = websocket.WebSocketApp(
    self.ws_url,
    on_open=self.on_open,
    on_message=self.on_message,
    on_error=self.on_error,
    on_close=self.on_close
)
```

2. **Authentication Problems**
```python
# Verify handshake packet
handshake_packet = self.create_handshake_packet()
ws.send(handshake_packet, ABNF.OPCODE_BINARY)
```

3. **Message Parsing Errors**
- Check message format
- Verify JSON structure
- Monitor decompression process

## Project Structure

```
Tofu-Danmaku/
├── main.py                     # Main application entry point
├── src/                        # Source code directory
│   ├── bili_danmaku_client.py # WebSocket client implementation
│   ├── parser_handler.py      # Message parsing and handling
│   ├── room_history.py       # Room history management
│   ├── packet.py            # WebSocket packet creation
│   └── fetch.py            # Server info retrieval
├── requirements.txt           # Python dependencies
├── Dockerfile                # Docker configuration
├── .danmaku_input_history   # Command history storage
├── LICENSE                  # License information
└── README.md               # Project documentation
```

## Contributing

We welcome contributions! Here's how you can help:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

Please ensure your code follows the project's coding style and includes appropriate tests.

## License

This project is licensed under the terms included in the LICENSE file. See the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Thanks to the Bilibili API community
- All contributors who have helped improve this project
- The open-source projects that made this possible

## Contact

For bug reports and feature requests, please use the GitHub issue tracker.

---

<a name="chinese"></a>
# 豆腐弹幕姬

基于 Python 的哔哩哔哩（B站）直播弹幕客户端，支持实时连接直播间并接收弹幕消息。

## 功能特点

- 通过房间号连接 B站直播间
- 实时显示弹幕消息
- 保存并管理房间历史记录
- 支持命令历史记录快速导航
- 可选的爬虫模式用于监控直播间状态
- 命令行界面支持
- Docker 容器化部署支持
- 跨平台兼容（Windows、macOS、Linux）
- 高级 PK 对战监控和分析
- 关键词检测系统
- 基于 WebSocket 的实时通信
- 自动心跳包管理

## 环境要求

- Python 3.x
- brotli
- websocket-client
- requests

## 安装方法

### 方法一：直接安装

1. 克隆仓库：
```bash
git clone https://github.com/yourusername/Tofu-Danmaku.git
cd Tofu-Danmaku
```

2. 安装依赖：
```bash
pip install -r requirements.txt
```

### 方法二：使用 Docker

1. 构建 Docker 镜像：
```bash
docker build -t tofu-danmaku .
```

2. 运行容器：
```bash
docker run -it tofu-danmaku
```

## 技术细节

### 核心组件

1. **B站弹幕客户端 (`bili_danmaku_client.py`)**
   - WebSocket 客户端主要实现
   - 处理连接管理
   - 实现自动心跳机制
   - 管理认证和服务器通信

2. **消息解析器 (`parser_handler.py`)**
   - 处理接收到的 WebSocket 消息
   - 支持多种消息类型：
     - 弹幕消息
     - PK 对战信息
     - 房间状态更新
   - 实现关键词检测
   - 管理 PK 对战监控

3. **房间历史管理器 (`room_history.py`)**
   - 维护连接历史记录
   - 管理房间备注和元数据
   - 提供历史记录导航

4. **网络组件**
   - `fetch.py`：处理服务器信息获取
   - `packet.py`：管理 WebSocket 数据包创建

### 消息类型

客户端处理以下几种类型的消息：

1. **弹幕消息**
   - 普通聊天消息
   - 特殊指令
   - 系统通知

2. **PK 对战信息**
   - 对战进度更新
   - 投票计数
   - 金币计数
   - 对战状态变化

3. **房间状态更新**
   - 直播状态变化
   - 房间配置更新
   - 观看人数更新

## 高级功能

### PK 对战监控

系统支持两种类型的 PK 对战：

1. **类型 1 PK 对战**
```python
python main.py --room-id <房间号> --spider
```
- 监控初始对战设置
- 追踪投票计数
- 分析对战进度
- 基于条件触发提醒

2. **类型 2 PK 对战**
- 监控扩展对战信息
- 同时追踪投票和金币计数
- 提供详细的对战分析

### 关键词检测

系统监控特定关键词的消息：
- 默认关键词："观测站"、"鱼豆腐"
- 可通过代码修改自定义关键词
- 关键词匹配时实时通知

### 爬虫模式功能

启用爬虫模式时：
1. 监控 STOP_LIVE_ROOM_LIST 消息
2. 追踪房间状态变化
3. 提供扩展数据收集
4. 启用高级分析功能

## 监控和调试

### 日志消息

系统使用不同的表情符号标识日志消息：
- ✅ 成功消息
- ❌ 错误消息
- 📊 统计数据
- 🔄 进程更新
- ⏱️ 计时器事件
- 🔍 检查结果

### 常见调试点

1. **连接问题**
```python
# 检查 WebSocket 连接
ws = websocket.WebSocketApp(
    self.ws_url,
    on_open=self.on_open,
    on_message=self.on_message,
    on_error=self.on_error,
    on_close=self.on_close
)
```

2. **认证问题**
```python
# 验证握手包
handshake_packet = self.create_handshake_packet()
ws.send(handshake_packet, ABNF.OPCODE_BINARY)
```

3. **消息解析错误**
- 检查消息格式
- 验证 JSON 结构
- 监控解压缩过程

## 项目结构

```
Tofu-Danmaku/
├── main.py                     # 主程序入口
├── src/                        # 源代码目录
│   ├── bili_danmaku_client.py # WebSocket 客户端实现
│   ├── parser_handler.py      # 消息解析和处理
│   ├── room_history.py       # 房间历史记录管理
│   ├── packet.py            # WebSocket 数据包创建
│   └── fetch.py            # 服务器信息获取
├── requirements.txt           # Python 依赖
├── Dockerfile                # Docker 配置
├── .danmaku_input_history   # 命令历史记录存储
├── LICENSE                  # 许可证信息
└── README.md               # 项目文档
```

## 参与贡献

我们欢迎各种形式的贡献！以下是参与方式：

1. Fork 本仓库
2. 创建特性分支
3. 提交更改
4. 提交 Pull Request

请确保您的代码符合项目的代码风格并包含适当的测试。

## 许可证

本项目基于 LICENSE 文件中包含的条款进行许可。详情请参见 [LICENSE](LICENSE) 文件。

## 致谢

- 感谢 B站 API 社区
- 感谢所有帮助改进这个项目的贡献者
- 感谢使这个项目成为可能的开源项目

## 联系方式

如有 bug 报告和功能请求，请使用 GitHub issue 追踪器。

---
用 ❤️ 为 B站 社区制作
