"""新版本的B站直播消息处理入口文件

用于替代旧版的parser_handler.py，提供更好的模块化设计
"""

import logging
from bili_live.logger import setup_logger
from bili_live.parser import BiliMessageParser


def main(room_id: int, api_url: str = None, enable_spider: bool = False, log_file: str = None, debug: bool = False):
    """主函数
    
    Args:
        room_id: 直播间ID
        api_url: API服务器URL，None则使用默认值
        enable_spider: 是否启用爬虫功能
        log_file: 日志文件路径
        debug: 是否开启调试模式
    """
    # 设置日志
    level = logging.DEBUG if debug else logging.INFO
    logger = setup_logger("bili_live", level=level, log_file=log_file)
    
    logger.info(f"🚀 启动B站直播消息处理器，房间ID: {room_id}")
    logger.info(f"🔧 爬虫功能: {'启用' if enable_spider else '禁用'}")
    
    # 创建解析器
    parser = BiliMessageParser(
        room_id=room_id, 
        api_base_url=api_url, 
        spider=bool(enable_spider)  # 确保是布尔值
    )
    
    # 注意: 这里仅创建解析器，实际的WebSocket连接和消息接收
    # 应该在外部实现，然后调用parser.parse_message(data)处理消息
    
    logger.info("✅ 解析器初始化完成，准备接收消息")
    
    return parser


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="B站直播消息处理器")
    parser.add_argument("room_id", type=int, help="直播间ID")
    parser.add_argument("--api", type=str, help="API服务器URL")
    parser.add_argument("--spider", action="store_true", help="启用爬虫功能")
    parser.add_argument("--log", type=str, help="日志文件路径")
    parser.add_argument("--debug", action="store_true", help="开启调试模式")
    
    args = parser.parse_args()
    
    main(args.room_id, args.api, args.spider, args.log, args.debug) 