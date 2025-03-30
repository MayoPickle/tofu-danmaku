"""日志配置模块

为系统提供统一的日志配置
"""

import logging
import sys
from typing import Optional


def setup_logger(name: str = "bili_live", 
                 level: int = logging.INFO,
                 log_file: Optional[str] = None,
                 console: bool = True) -> logging.Logger:
    """设置日志记录器
    
    Args:
        name: 日志记录器名称
        level: 日志级别
        log_file: 日志文件路径，不提供则不记录到文件
        console: 是否在控制台输出
        
    Returns:
        logging.Logger: 配置好的日志记录器
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # 日志格式
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 清除现有处理器
    logger.handlers = []
    
    # 添加文件处理器
    if log_file:
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    # 添加控制台处理器
    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    return logger


# 创建默认日志记录器
default_logger = setup_logger() 