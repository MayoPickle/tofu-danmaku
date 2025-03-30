"""PK数据收集器模块

负责收集和分析B站直播PK相关数据
"""

import logging
from typing import Dict, Any, Tuple

from .constants import Constants

logger = logging.getLogger(__name__)


class PKDataCollector:
    """PK数据收集器
    
    负责收集、记录和分析PK相关数据
    """
    
    def __init__(self, room_id: int):
        """初始化PK数据收集器
        
        Args:
            room_id: 当前直播间ID
        """
        self.room_id = room_id
        self.last_pk_info = None
        self.last_battle_process = None
    
    def update_battle_process(self, message: Dict[str, Any]) -> None:
        """更新PK_BATTLE_PROCESS_NEW消息数据
        
        Args:
            message: PK战斗进程消息
        """
        self.last_battle_process = message
        self._log_battle_process_data(message)
    
    def update_info(self, message: Dict[str, Any]) -> None:
        """更新PK_INFO消息数据
        
        Args:
            message: PK信息消息
        """
        self.last_pk_info = message
        self._log_pk_info_data(message)
    
    def get_pk_data(self, battle_type: int) -> Dict[str, Any]:
        """根据PK类型获取相应数据
        
        Args:
            battle_type: PK类型（1或2）
            
        Returns:
            Dict: PK相关数据
        """
        if battle_type == Constants.PK_TYPE_1:
            return self.last_battle_process.get("data", {}) if self.last_battle_process else {}
        else:
            return self.last_pk_info.get("data", {}) if self.last_pk_info else {}
    
    def get_votes_data(self, battle_type: int) -> Tuple[int, int]:
        """获取己方和对方的票数数据
        
        Args:
            battle_type: PK类型（1或2）
            
        Returns:
            Tuple[int, int]: (己方票数, 对方票数)
        """
        self_votes = 0
        opponent_votes = 0
        
        try:
            if battle_type == Constants.PK_TYPE_1 and self.last_battle_process:
                data = self.last_battle_process.get("data", {})
                init_info = data.get("init_info", {})
                match_info = data.get("match_info", {})
                
                init_votes = init_info.get("votes", 0)
                match_votes = match_info.get("votes", 0)
                init_room_id = init_info.get("room_id", None)
                
                if self.room_id == init_room_id:
                    self_votes = init_votes
                    opponent_votes = match_votes
                else:
                    self_votes = match_votes
                    opponent_votes = init_votes
                    
            elif battle_type == Constants.PK_TYPE_2 and self.last_pk_info:
                members = self.last_pk_info.get("data", {}).get("members", [])
                self_participant = None
                opponent = None
                
                for member in members:
                    if member.get("room_id") == self.room_id:
                        self_participant = member
                    else:
                        opponent = member
                
                if self_participant and opponent:
                    self_votes = self_participant.get("votes", 0)
                    opponent_votes = opponent.get("votes", 0)
        except Exception as e:
            logger.error(f"❌ 获取票数数据时出错: {e}")
        
        return self_votes, opponent_votes
    
    def _log_battle_process_data(self, message: Dict[str, Any]) -> None:
        """记录PK_BATTLE_PROCESS_NEW消息的详细信息
        
        Args:
            message: PK战斗进程消息
        """
        try:
            if "data" in message and "init_info" in message["data"] and "match_info" in message["data"]:
                init_info = message["data"]["init_info"]
                match_info = message["data"]["match_info"]
                
                init_votes = init_info.get("votes", 0)
                match_votes = match_info.get("votes", 0)
                init_room_id = init_info.get("room_id", "未知")
                match_room_id = match_info.get("room_id", "未知")
                
                if self.room_id == init_room_id:
                    self_votes = init_votes
                    opponent_votes = match_votes
                    opponent_room_id = match_room_id
                else:
                    self_votes = match_votes
                    opponent_votes = init_votes
                    opponent_room_id = init_room_id
                
                logger.info(f"📊 PK进程数据: 房间={self.room_id}, 己方票数={self_votes}, 对方房间={opponent_room_id}, 对方票数={opponent_votes}")
                
                # 打印所有可能的票数相关字段以便调试
                all_fields = []
                for source, prefix in [(init_info, "init"), (match_info, "match")]:
                    for key, value in source.items():
                        if isinstance(value, (int, float)) or (isinstance(value, str) and value.isdigit()):
                            all_fields.append(f"{prefix}.{key}={value}")
                
                if all_fields:
                    logger.debug(f"🔢 数值字段: {', '.join(all_fields)}")
        except Exception as e:
            logger.error(f"❌ 记录battle_process日志时出错: {e}")
        
        logger.info("✅ 更新了 PK_BATTLE_PROCESS_NEW 数据")
    
    def _log_pk_info_data(self, message: Dict[str, Any]) -> None:
        """记录PK_INFO消息的详细信息
        
        Args:
            message: PK信息消息
        """
        try:
            if "data" in message and "members" in message["data"]:
                members = message["data"]["members"]
                self_participant = None
                opponent = None
                
                # 找出己方和对方
                for member in members:
                    if "room_id" in member and member["room_id"] == self.room_id:
                        self_participant = member
                    else:
                        opponent = member
                
                # 详细记录所有成员信息
                if members:
                    logger.info(f"👥 PK总成员数: {len(members)}")
                    for i, member in enumerate(members):
                        room_id = member.get("room_id", "未知")
                        votes = member.get("votes", 0)
                        golds = member.get("golds", 0)
                        is_self = "✓" if room_id == self.room_id else "✗"
                        logger.debug(f"👤 成员{i+1}: 房间={room_id} {is_self}, 票数={votes}, 金币={golds}")
                
                # 汇总己方和对方的票数信息
                if self_participant and opponent:
                    votes_self = self_participant.get("votes", 0)
                    votes_opponent = opponent.get("votes", 0)
                    golds_self = self_participant.get("golds", 0)
                    golds_opponent = opponent.get("golds", 0)
                    opponent_room_id = opponent.get("room_id", "未知")
                    
                    logger.info(f"📊 PK信息汇总: 房间={self.room_id}, 己方票数={votes_self}, 己方金币={golds_self}, "
                               f"对方房间={opponent_room_id}, 对方票数={votes_opponent}, 对方金币={golds_opponent}")
                    
                    # 记录票数差距和比例
                    votes_diff = votes_self - votes_opponent
                    total_votes = votes_self + votes_opponent
                    
                    if votes_diff > 0:
                        logger.info(f"🥇 己方领先 {votes_diff} 票")
                    elif votes_diff < 0:
                        logger.info(f"🥈 对方领先 {abs(votes_diff)} 票")
                    else:
                        logger.info("🔄 双方票数持平")
                    
                    if total_votes > 0:
                        self_percentage = (votes_self / total_votes) * 100
                        opponent_percentage = (votes_opponent / total_votes) * 100
                        logger.info(f"📈 票数比例: 己方 {self_percentage:.1f}%, 对方 {opponent_percentage:.1f}%")
        except Exception as e:
            logger.error(f"❌ 记录pk_info日志时出错: {e}")
        
        logger.info("✅ 更新了 PK_INFO 数据") 