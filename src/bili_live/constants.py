"""常量定义模块

定义整个项目中使用的常量值，便于集中管理和配置
"""


class Constants:
    """系统常量定义"""
    
    # API相关常量
    DEFAULT_TIMEOUT = 3
    DEFAULT_API_TOKEN = "8096"
    DEFAULT_API_URL = "http://192.168.0.102:8081"
    
    # 弹幕关键词
    KEYWORDS = ["观测站", "鱼豆腐"]
    ROBOT_KEYWORD = "记仇机器人"
    
    # PK 相关常量
    PK_TYPE_1 = 1
    PK_TYPE_2 = 2
    PK_DELAYED_CHECK_TIME = 170  # 秒
    PK_END_CHECK_TIME = 290  # 秒
    PK_OPPONENT_VOTES_THRESHOLD = 100
    
    # 消息类型
    MSG_DANMU = "DANMU_MSG"
    MSG_GIFT = "SEND_GIFT"
    MSG_PK_START = "PK_BATTLE_START_NEW"
    MSG_PK_END = "PK_BATTLE_END"
    MSG_PK_INFO = "PK_INFO"
    MSG_PK_PROCESS = "PK_BATTLE_PROCESS_NEW"
    MSG_LIVE_ROOM_LIST = "STOP_LIVE_ROOM_LIST"
    
    # API路径
    API_PK = "pk_wanzun"
    API_TICKET = "ticket"
    API_SETTING = "setting"
    API_MONEY = "money"
    API_LIVE_ROOM_SPIDER = "live_room_spider" 