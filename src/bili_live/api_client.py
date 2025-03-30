"""API客户端模块

提供与外部API通信的功能
"""

import logging
import requests
from typing import Dict, Any

from .constants import Constants

logger = logging.getLogger(__name__)


class APIClient:
    """API客户端
    
    负责与外部API服务器通信，发送各种事件数据
    """
    
    def __init__(self, base_url: str = Constants.DEFAULT_API_URL):
        """初始化API客户端
        
        Args:
            base_url: API服务器的基础URL
        """
        self.base_url = base_url

    def post(self, endpoint: str, payload: Dict[str, Any]) -> bool:
        """发送POST请求到指定端点
        
        Args:
            endpoint: API端点路径
            payload: 要发送的数据
            
        Returns:
            bool: 请求是否成功
        """
        url = f"{self.base_url}/{endpoint}"
        try:
            response = requests.post(url, json=payload, timeout=Constants.DEFAULT_TIMEOUT)
            if response.status_code == 200:
                logger.info(f"✅ 请求成功发送至 {url}")
                return True
            else:
                logger.error(f"❌ 请求失败，HTTP 状态码: {response.status_code}")
                return False
        except requests.RequestException as e:
            logger.error(f"❌ 请求异常: {e}")
            return False 