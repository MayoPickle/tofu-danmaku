import json
import zlib
import brotli
import requests
import threading
import logging
import sys
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Callable, Union
from dataclasses import dataclass

# 导入配置
from .config import (
    API_BASE_URL,
    DEFAULT_TIMEOUT, 
    DEFAULT_API_TOKEN,
    KEYWORDS,
    ROBOT_KEYWORD,
    CHATBOT_KEYWORDS,
    BLOCKED_USERNAME_PREFIXES,
    PK_DELAYED_CHECK_TIME,
    PK_END_CHECK_TIME,
    PK_OPPONENT_VOTES_THRESHOLD,
    GUARD_MODE_KEYWORDS,
    GUARD_MODE_VOTE_DIFFERENCE
)

# 配置日志，确保在 Docker 中也能正确输出
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ],
    force=True  # 强制重新配置日志
)
logger = logging.getLogger(__name__)

# 确保日志立即输出
for handler in logger.handlers:
    handler.flush = lambda: sys.stdout.flush()


# 常量定义
class Constants:
    DEFAULT_TIMEOUT = DEFAULT_TIMEOUT
    DEFAULT_API_TOKEN = DEFAULT_API_TOKEN
    KEYWORDS = KEYWORDS
    ROBOT_KEYWORD = ROBOT_KEYWORD
    CHATBOT_KEYWORDS = CHATBOT_KEYWORDS  # 改为列表，包含多个关键词
    BLOCKED_USERNAME_PREFIXES = BLOCKED_USERNAME_PREFIXES  # 被屏蔽的用户名前缀列表
    
    # PK 相关常量
    PK_TYPE_1 = 1
    PK_TYPE_2 = 2
    PK_DELAYED_CHECK_TIME = PK_DELAYED_CHECK_TIME  # 秒
    PK_END_CHECK_TIME = PK_END_CHECK_TIME  # 秒
    PK_OPPONENT_VOTES_THRESHOLD = PK_OPPONENT_VOTES_THRESHOLD
    
    # 保卫模式相关常量
    GUARD_MODE_KEYWORDS = GUARD_MODE_KEYWORDS
    GUARD_MODE_VOTE_DIFFERENCE = GUARD_MODE_VOTE_DIFFERENCE


# API 客户端
class APIClient:
    def __init__(self, base_url: str):
        self.base_url = base_url

    def post(self, endpoint: str, payload: Dict[str, Any]) -> tuple:
        """发送 POST 请求到指定端点
        
        Returns:
            tuple: (成功标志, 状态码或None)
        """
        url = f"{self.base_url}/{endpoint}"
        try:
            response = requests.post(url, json=payload, timeout=Constants.DEFAULT_TIMEOUT)
            status_code = response.status_code
            if status_code == 200:
                logger.info(f"✅ 请求成功发送至 {url}")
                return True, status_code
            else:
                logger.error(f"❌ 请求失败，HTTP 状态码: {status_code}")
                return False, status_code
        except requests.RequestException as e:
            logger.error(f"❌ 请求异常: {e}")
            return False, None


# 事件处理器基类
class EventHandler(ABC):
    @abstractmethod
    def handle(self, message: Dict[str, Any]) -> None:
        """处理事件消息"""
        pass
    
    @abstractmethod
    def stop(self) -> None:
        """停止处理器"""
        pass


# PK 数据收集器
class PKDataCollector:
    def __init__(self, room_id: int):
        self.room_id = room_id
        self.last_pk_info = None
        self.last_battle_process = None
    
    def update_battle_process(self, message: Dict[str, Any]) -> None:
        """更新 PK_BATTLE_PROCESS_NEW 消息数据"""
        self.last_battle_process = message
        self._log_battle_process_data(message)
    
    def update_info(self, message: Dict[str, Any]) -> None:
        """更新 PK_INFO 消息数据"""
        self.last_pk_info = message
        self._log_pk_info_data(message)
    
    def get_pk_data(self, battle_type: int) -> Dict[str, Any]:
        """根据 PK 类型获取相应数据"""
        if battle_type == Constants.PK_TYPE_1:
            return self.last_battle_process.get("data", {}) if self.last_battle_process else {}
        else:
            return self.last_pk_info.get("data", {}) if self.last_pk_info else {}
    
    def get_votes_data(self, battle_type: int) -> tuple:
        """获取己方和对方的票数数据"""
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
        """记录 PK_BATTLE_PROCESS_NEW 消息的详细信息"""
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
        """记录 PK_INFO 消息的详细信息"""
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


# 保卫模式管理器
class GuardModeManager:
    """保卫模式管理器
    
    负责管理保卫模式的激活状态和相关逻辑
    """
    
    def __init__(self):
        self.is_active = False
        self.activated_keyword = None
        self.lock = threading.Lock()
    
    def activate(self, keyword: str) -> bool:
        """激活保卫模式
        
        Args:
            keyword: 激活保卫模式的关键词
            
        Returns:
            bool: 是否成功激活
        """
        with self.lock:
            if not self.is_active:
                self.is_active = True
                self.activated_keyword = keyword
                logger.info(f"🛡️ 保卫模式已激活，触发关键词：'{keyword}'")
                return True
            else:
                logger.info(f"⚠️ 保卫模式已经处于激活状态，忽略关键词：'{keyword}'")
                return False
    
    def deactivate(self) -> None:
        """关闭保卫模式"""
        with self.lock:
            if self.is_active:
                logger.info(f"🛡️ 保卫模式已关闭，之前的触发关键词：'{self.activated_keyword}'")
                self.is_active = False
                self.activated_keyword = None
            else:
                logger.debug("保卫模式本来就是关闭状态")
    
    def is_guard_mode_active(self) -> bool:
        """检查保卫模式是否激活"""
        with self.lock:
            return self.is_active
    
    def get_activated_keyword(self) -> Optional[str]:
        """获取激活保卫模式的关键词"""
        with self.lock:
            return self.activated_keyword


# 全局保卫模式管理器实例
guard_mode_manager = GuardModeManager()


# PK 战斗处理器
class PKBattleHandler(EventHandler):
    def __init__(self, room_id: int, api_client: APIClient, battle_type: int):
        self.room_id = room_id
        self.api_client = api_client
        self.battle_type = self._normalize_battle_type(battle_type)
        self.data_collector = PKDataCollector(room_id)
        self.pk_triggered = False
        
        # 初始化定时器
        self.delayed_check_timer = threading.Timer(Constants.PK_DELAYED_CHECK_TIME, self.delayed_check)
        self.end_timer = threading.Timer(Constants.PK_END_CHECK_TIME, self.end_check)
        
        # 启动定时器
        self.delayed_check_timer.start()
        self.end_timer.start()
        
        logger.info(f"✅ PKBattleHandler 初始化完成，battle_type={self.battle_type}，定时器已启动")
    
    def _normalize_battle_type(self, battle_type: int) -> int:
        """标准化 PK 类型，将非类型1的所有 PK 归为类型2处理"""
        logger.info(f"🔄 PKBattleHandler 初始化，原始battle_type={battle_type}")
        
        if battle_type != Constants.PK_TYPE_1:
            logger.info(f"📝 将battle_type从{battle_type}调整为{Constants.PK_TYPE_2}进行统一处理")
            return Constants.PK_TYPE_2
        return battle_type
    
    def handle(self, message: Dict[str, Any]) -> None:
        """处理 PK 消息"""
        cmd = message.get("cmd", "")
        
        if cmd == "PK_INFO":
            self.data_collector.update_info(message)
        elif cmd == "PK_BATTLE_PROCESS_NEW":
            self.data_collector.update_battle_process(message)
    
    def delayed_check(self) -> None:
        """根据 PK 类型和票数触发绝杀计时器"""
        logger.info("⏱️ 绝杀 PK 定时器触发")
        
        if self.pk_triggered:
            logger.info("❌ PK 已经被触发过，跳过检查")
            return
        
        try:
            self_votes, opponent_votes = self.data_collector.get_votes_data(self.battle_type)
            
            logger.info(f"🔍 battle_type={self.battle_type} 检查: 房间={self.room_id}, 己方votes={self_votes}, 对方votes={opponent_votes}")
            
            if self_votes == 0 and opponent_votes > Constants.PK_OPPONENT_VOTES_THRESHOLD:
                logger.info(f"❗ 对手 votes > {Constants.PK_OPPONENT_VOTES_THRESHOLD} 且本房间 votes == 0，触发 API")
                self.pk_triggered = True
                self.cancel_end_timer()
                self.trigger_api()
            else:
                logger.info(f"✅ 绝杀条件不满足，不触发 API: self_votes={self_votes}, opponent_votes={opponent_votes}")
        except Exception as e:
            logger.error(f"❌ 绝杀检查出错: {e}")
    
    def end_check(self) -> None:
        """结束计时器逻辑"""
        logger.info("⏱️ 结束计时器触发")
        
        if self.pk_triggered:
            logger.info("❌ PK 已经被触发过，跳过结束检查")
            return
        
        try:
            self_votes, opponent_votes = self.data_collector.get_votes_data(self.battle_type)
            
            logger.info(f"🔍 结束检查 battle_type={self.battle_type}: 己方votes={self_votes}, 对方votes={opponent_votes}")
            
            # 检查保卫模式是否激活
            if guard_mode_manager.is_guard_mode_active():
                activated_keyword = guard_mode_manager.get_activated_keyword()
                target_votes = opponent_votes + Constants.GUARD_MODE_VOTE_DIFFERENCE
                
                logger.info(f"🛡️ 保卫模式激活中，触发关键词：'{activated_keyword}'")
                logger.info(f"🎯 保卫模式目标：对方{opponent_votes}票，将发送{target_votes}票")
                
                self.pk_triggered = True
                self.trigger_guard_mode_api(target_votes, activated_keyword)
            elif self_votes == 0:
                # 原有的结束检查逻辑
                logger.info("⚠️ 结束检查：己方票数为0，将触发API")
                self.pk_triggered = True
                self.trigger_api()
            else:
                logger.info(f"✅ 结束检查：己方票数不为0 ({self_votes})，不触发API")
        except Exception as e:
            logger.error(f"❌ 结束检查出错: {e}")
    
    def cancel_end_timer(self) -> None:
        """取消结束计时器"""
        if self.end_timer:
            self.end_timer.cancel()
            logger.info("✅ 已取消结束计时器")
    
    def stop(self) -> None:
        """销毁计时器"""
        if self.delayed_check_timer:
            self.delayed_check_timer.cancel()
        if self.end_timer:
            self.end_timer.cancel()
        
        # PK结束时关闭保卫模式
        guard_mode_manager.deactivate()
        
        logger.info("🛑 停止计时器并销毁 PKBattleHandler 实例")
    
    def trigger_api(self) -> None:
        """触发 API"""
        pk_data = self.data_collector.get_pk_data(self.battle_type)
        
        payload = {
            "room_id": self.room_id,
            "battle_type": self.battle_type,
            "pk_data": pk_data,
            "token": Constants.DEFAULT_API_TOKEN
        }
        
        self.api_client.post("pk_wanzun", payload)
    
    def trigger_guard_mode_api(self, target_votes: int, activated_keyword: str) -> None:
        """触发保卫模式 API
        
        Args:
            target_votes: 目标票数
            activated_keyword: 激活保卫模式的关键词
        """
        pk_data = self.data_collector.get_pk_data(self.battle_type)
        
        payload = {
            "room_id": self.room_id,
            "battle_type": self.battle_type,
            "pk_data": pk_data,
            "token": Constants.DEFAULT_API_TOKEN,
            "guard_mode": True,
            "target_votes": target_votes,
            "activated_keyword": activated_keyword
        }
        
        success, _ = self.api_client.post("pk_wanzun", payload)
        if success:
            logger.info(f"🛡️ 保卫模式API调用成功：目标票数={target_votes}，关键词='{activated_keyword}'")
        else:
            logger.error(f"❌ 保卫模式API调用失败：目标票数={target_votes}，关键词='{activated_keyword}'")


# 弹幕处理器
class DanmakuHandler(EventHandler):
    def __init__(self, room_id: int, api_client: APIClient):
        self.room_id = room_id
        self.api_client = api_client
    
    def handle(self, message: Dict[str, Any]) -> None:
        """处理弹幕消息"""
        info = message.get("info", [])
        if len(info) > 2:
            comment = info[1]
            username = info[2][1]
            
            # 使用 print 确保弹幕立即输出，同时保留日志
            danmaku_msg = f"[{username}] {comment}"
            print(danmaku_msg, flush=True)  # 添加 flush=True 确保立即输出
            logger.info(danmaku_msg)
            
            # 检查用户名是否以"观"开头，如果是则不处理
            if username.startswith("观"):
                ignore_msg = f"⛔ 忽略来自以'观'开头的用户的消息: [{username}] '{comment}'"
                print(ignore_msg, flush=True)
                logger.info(ignore_msg)
                return
            
            # 关键词检测
            self._keyword_detection(comment, message)
            
            # chatbot关键词检测和点赞检测
            if any(keyword in comment for keyword in Constants.CHATBOT_KEYWORDS):
                modified_comment = comment
                
                # 检查是否是豆豆+点赞组合，如果是则先处理sendlike
                if "豆豆" in comment and "点赞" in comment:
                    error_msg = self._sendlike_detection(comment, message)
                    if error_msg:
                        # 如果有错误信息，则将其附加到原始消息后
                        modified_comment = f"{comment} {error_msg}"
                
                # 然后再处理chatbot
                self._chatbot_detection(modified_comment, message)
                
                # 保卫模式检测（需要先激活豆豆）
                self._guard_mode_detection(comment, message)
            
            # 机器人指令检测
            if Constants.ROBOT_KEYWORD in comment:
                self._send_to_setting(comment, message)
    
    def _keyword_detection(self, danmaku: str, raw_message: Dict[str, Any]) -> None:
        """检测弹幕内容是否包含关键字并发送 POST 请求"""
        if any(keyword in danmaku for keyword in Constants.KEYWORDS):
            payload = {
                "room_id": self.room_id,
                "danmaku": danmaku,
                "raw_message": raw_message
            }
            success, _ = self.api_client.post("ticket", payload)
            if success:
                logger.info(f"✅ 关键字检测成功：'{danmaku}' 已发送至 ticket 接口")
    
    def _chatbot_detection(self, danmaku: str, raw_message: Dict[str, Any]) -> None:
        """检测弹幕内容是否包含chatbot关键词并发送到 chatbot 接口"""
        # 记录触发的关键词
        triggered_keywords = [keyword for keyword in Constants.CHATBOT_KEYWORDS if keyword in danmaku]
        keywords_str = "、".join(triggered_keywords)
        
        logger.info(f"🤖 检测到chatbot关键词「{keywords_str}」：'{danmaku}'")
        
        # 从原始消息中提取发送者名字（info[2][1]）
        sender_name = None
        try:
            info = raw_message.get("info", [])
            if isinstance(info, list) and len(info) > 2 and isinstance(info[2], list) and len(info[2]) > 1:
                sender_name = info[2][1]
        except Exception:
            sender_name = None

        # 组装更结构化的 payload
        uid = None
        uname = sender_name
        face_url = None
        wealth_level = None
        guard_level = None
        is_captain = False
        name_color = None
        official_role = None
        official_title = None
        medal_payload: Dict[str, Any] = {}
        ts = None
        message_id = None

        # 从 raw_message.info 中尽量提取有用信息（健壮判定，避免 KeyError）
        try:
            info = raw_message.get("info", [])
            # 基础 uid/uname（info[2] 常见为 [uid, uname, ...]）
            if isinstance(info, list) and len(info) > 2 and isinstance(info[2], list):
                try:
                    uid = info[2][0]
                except Exception:
                    uid = uid
                try:
                    if not uname:
                        uname = info[2][1]
                except Exception:
                    pass

            # 勋章（info[3] 通常是勋章数组）
            if isinstance(info, list) and len(info) > 3 and isinstance(info[3], list):
                m = info[3]
                try:
                    # 约定映射：
                    # [level, medal_name, anchor_uname, anchor_uid, color, "", 0, color_start, color_end, color_border, 0, is_light, ruid]
                    medal_payload_candidate: Dict[str, Any] = {}
                    if len(m) >= 2 and isinstance(m[1], str):
                        medal_payload_candidate["name"] = m[1]
                    if len(m) >= 1:
                        medal_payload_candidate["level"] = m[0]
                    if len(m) >= 4:
                        medal_payload_candidate["anchor_uid"] = m[3]
                    if len(m) >= 3 and isinstance(m[2], str):
                        medal_payload_candidate["anchor_uname"] = m[2]
                    if len(m) >= 5:
                        medal_payload_candidate["color"] = m[4]
                    if len(m) >= 12:
                        medal_payload_candidate["is_light"] = m[11]
                    if len(m) >= 9:
                        medal_payload_candidate["color_end"] = m[8]
                    if len(m) >= 8:
                        medal_payload_candidate["color_start"] = m[7]
                    if len(m) >= 10:
                        medal_payload_candidate["color_border"] = m[9]
                    # ruid 可能在不同实现中索引不同，尽量兜底
                    if len(m) >= 14:
                        medal_payload_candidate["ruid"] = m[13]
                    medal_payload = {k: v for k, v in medal_payload_candidate.items() if v is not None}
                except Exception:
                    pass

            # 查找包含 user/extra 的头部对象（通常在 info[0] 列表中的一个 dict）
            header_obj = None
            if isinstance(info, list) and len(info) > 0 and isinstance(info[0], list):
                for elem in info[0]:
                    if isinstance(elem, dict):
                        header_obj = elem
                        break

            if isinstance(header_obj, dict):
                # 解析 extra（字符串 JSON），提取 id_str、content 等
                extra_str = header_obj.get("extra")
                if isinstance(extra_str, str):
                    try:
                        extra = json.loads(extra_str)
                        message_id = extra.get("id_str") or message_id
                        # content 可与 danmaku 一致，一并保留
                    except Exception:
                        pass

                # 解析 user.base/wealth/guard 等
                user_block = header_obj.get("user")
                if isinstance(user_block, dict):
                    base = user_block.get("base") or {}
                    if isinstance(base, dict):
                        face_url = base.get("face") or face_url
                        name_color = base.get("name_color_str") or base.get("name_color") or name_color
                        official = base.get("official_info") or {}
                        if isinstance(official, dict):
                            official_role = official.get("role")
                            official_title = official.get("title")
                    wealth = user_block.get("wealth")
                    if isinstance(wealth, dict):
                        wealth_level = wealth.get("level", wealth_level)
                    guard = user_block.get("guard")
                    if isinstance(guard, dict):
                        guard_level = guard.get("level", guard_level)
                    # 是否舰长：guard_level==3 可视为舰长
                    is_captain = (guard_level == 3) or bool(user_block.get("guard_leader", {}).get("is_guard_leader"))

            # 从尾部的 dict 提取 ts（时间戳）
            if isinstance(info, list):
                for part in reversed(info):
                    if isinstance(part, dict) and "ts" in part:
                        ts = part.get("ts")
                        break
        except Exception:
            pass

        # 仅添加非空字段，保持 payload 简洁
        sender_payload: Dict[str, Any] = {}
        if uid is not None:
            sender_payload["uid"] = uid
        if uname:
            sender_payload["uname"] = uname
        if face_url:
            sender_payload["face"] = face_url
        if wealth_level is not None:
            sender_payload["wealth_level"] = wealth_level
        if guard_level is not None:
            sender_payload["guard_level"] = guard_level
        if name_color is not None:
            sender_payload["name_color"] = name_color
        if official_role is not None:
            sender_payload["official_role"] = official_role
        if official_title:
            sender_payload["official_title"] = official_title
        sender_payload["is_captain"] = bool(is_captain)

        meta_payload: Dict[str, Any] = {}
        if ts is not None:
            meta_payload["ts"] = ts
        if message_id:
            meta_payload["message_id"] = message_id
        if triggered_keywords:
            meta_payload["triggered_keywords"] = triggered_keywords

        chatbot_payload: Dict[str, Any] = {
            "room_id": str(self.room_id),
            "message": danmaku,
            "raw_message": raw_message
        }
        # 兼容旧字段：顶层仍保留 uname
        if uname:
            chatbot_payload["uname"] = uname
        if sender_payload:
            chatbot_payload["sender"] = sender_payload
        if medal_payload:
            chatbot_payload["medal"] = medal_payload
        if meta_payload:
            chatbot_payload["meta"] = meta_payload

        success, _ = self.api_client.post("chatbot", chatbot_payload)
        if success:
            logger.info(f"✅ 已将消息 '{danmaku}' 发送到 chatbot 接口")
        else:
            logger.error(f"❌ 消息 '{danmaku}' 发送到 chatbot 接口失败")
    
    def _sendlike_detection(self, danmaku: str, raw_message: Dict[str, Any]) -> Optional[str]:
        """发送包含豆豆和点赞的消息到 sendlike 接口
        
        Returns:
            Optional[str]: 如果发生错误，返回错误信息；如果成功，返回None
        """
        logger.info(f"👍 检测到豆豆+点赞组合：'{danmaku}'")
        
        sendlike_payload = {
            "room_id": str(self.room_id),
            "message": danmaku,
            "raw_message": raw_message
        }
        success, status_code = self.api_client.post("sendlike", sendlike_payload)
        
        if success:
            logger.info(f"✅ 已将消息 '{danmaku}' 发送到 sendlike 接口")
            return None
        else:
            error_msg = f"（已触发点赞服务，但服务器返回{status_code or '未知错误'}）"
            logger.error(f"❌ 消息 '{danmaku}' 发送到 sendlike 接口失败: {status_code}")
            return error_msg
    
    def _send_to_setting(self, danmaku: str, raw_message: Dict[str, Any]) -> None:
        """将包含"记仇机器人"的弹幕发送到 /setting 接口"""
        payload = {
            "room_id": self.room_id,
            "danmaku": danmaku,
            "raw_message": raw_message
        }
        success, _ = self.api_client.post("setting", payload)
        if success:
            logger.info(f"✅ 记仇机器人指令：'{danmaku}' 已发送")
    
    def _guard_mode_detection(self, danmaku: str, raw_message: Dict[str, Any]) -> None:
        """检测弹幕内容是否包含保卫模式关键词并激活保卫模式"""
        for keyword in Constants.GUARD_MODE_KEYWORDS:
            if keyword in danmaku:
                success = guard_mode_manager.activate(keyword)
                if success:
                    logger.info(f"🛡️ 保卫模式已激活，触发关键词：'{keyword}'，完整消息：'{danmaku}'")
                    
                    # 将关键词也发送给接口
                    payload = {
                        "room_id": self.room_id,
                        "danmaku": danmaku,
                        "guard_keyword": keyword,
                        "raw_message": raw_message
                    }
                    api_success, _ = self.api_client.post("guard_mode", payload)
                    if api_success:
                        logger.info(f"✅ 保卫模式关键词已发送至接口：'{keyword}'")
                    else:
                        logger.error(f"❌ 保卫模式关键词发送失败：'{keyword}'")
                break  # 只处理第一个匹配的关键词
    
    def stop(self) -> None:
        """停止处理器"""
        pass


# 礼物处理器
class GiftHandler(EventHandler):
    def __init__(self, room_id: int, api_client: APIClient):
        self.room_id = room_id
        self.api_client = api_client
    
    def handle(self, message: Dict[str, Any]) -> None:
        """处理礼物消息"""
        try:
            data = message.get("data", {})
            
            # 提取送礼信息
            uid = data.get("uid", 0)
            uname = data.get("uname", "")
            gift_id = data.get("giftId", 0)
            gift_name = data.get("giftName", "")
            price = data.get("price", 0)
            # 提取礼物数量
            gift_num = data.get("num", 1)  # 默认为1个
            
            # 如果有 sender_uinfo 就从那里获取更详细的用户信息
            if "sender_uinfo" in data and "base" in data["sender_uinfo"]:
                sender_base = data["sender_uinfo"]["base"]
                uid = data["sender_uinfo"].get("uid", uid)
                uname = sender_base.get("name", uname)
            
            # 打印礼物信息，包含数量
            logger.info(f"🎁 礼物: [{uname}] 赠送 [{gift_name}] x{gift_num}, 价值: {price * gift_num}")
            
            # 发送到 /money 接口，扩展更多有效字段
            total_price = (price or 0) * (gift_num or 1)
            payload = {
                "room_id": self.room_id,
                "uid": uid,
                "uname": uname,
                "gift_id": gift_id,
                "gift_name": gift_name,
                "gift_num": gift_num,
                "price": price,
                "total_price": total_price
            }

            # 基础补充字段
            coin_type = data.get("coin_type")
            gift_type = data.get("giftType")
            action = data.get("action")
            if coin_type is not None:
                payload["coin_type"] = coin_type
            if gift_type is not None:
                payload["gift_type"] = gift_type
            if action:
                payload["action"] = action

            # 盲盒相关（盈亏计算）
            blind_gift = data.get("blind_gift")
            if isinstance(blind_gift, dict):
                original_price = blind_gift.get("original_gift_price")
                original_id = blind_gift.get("original_gift_id")
                original_name = blind_gift.get("original_gift_name")
                tip_price = blind_gift.get("gift_tip_price")
                revealed_price = price
                diff = None
                if isinstance(original_price, (int, float)) and isinstance(revealed_price, (int, float)):
                    diff = revealed_price - original_price
                result = None
                if isinstance(diff, (int, float)):
                    if diff > 0:
                        result = "profit"
                    elif diff < 0:
                        result = "loss"
                    else:
                        result = "even"
                payload["is_blind_gift"] = True
                payload["blind_box"] = {
                    "original_gift_id": original_id,
                    "original_gift_name": original_name,
                    "original_gift_price": original_price,
                    "revealed_gift_id": gift_id,
                    "revealed_gift_name": gift_name,
                    "revealed_gift_price": revealed_price,
                    "gift_tip_price": tip_price,
                    "diff": diff,
                    "result": result
                }
            else:
                payload["is_blind_gift"] = False

            # 扩展发送者信息（头像、财富等级、守护、勋章、名称色）
            sender_payload: Dict[str, Any] = {}
            sender_uinfo = data.get("sender_uinfo") if isinstance(data, dict) else None
            if isinstance(sender_uinfo, dict):
                base = sender_uinfo.get("base") or {}
                if isinstance(base, dict):
                    face_url = base.get("face")
                    name_color = base.get("name_color_str") or base.get("name_color")
                    if face_url:
                        sender_payload["face"] = face_url
                    if name_color:
                        sender_payload["name_color"] = name_color
                # 财富等级
                wealth = sender_uinfo.get("wealth")
                if isinstance(wealth, dict) and "level" in wealth:
                    sender_payload["wealth_level"] = wealth.get("level")
                # 守护等级
                guard = sender_uinfo.get("guard")
                if isinstance(guard, dict) and "level" in guard:
                    sender_payload["guard_level"] = guard.get("level")
                # 勋章
                medal = sender_uinfo.get("medal")
                if isinstance(medal, dict):
                    sender_payload["medal"] = {
                        "name": medal.get("name"),
                        "level": medal.get("level"),
                        "is_light": medal.get("is_light"),
                        "ruid": medal.get("ruid"),
                        "guard_level": medal.get("guard_level"),
                        "color": medal.get("color"),
                        "color_start": medal.get("color_start"),
                        "color_end": medal.get("color_end"),
                        "color_border": medal.get("color_border")
                    }
            # 顶层 wealth_level/guard_level（有些事件会直接给出）
            if isinstance(data.get("wealth_level"), int) and "wealth_level" not in sender_payload:
                sender_payload["wealth_level"] = data.get("wealth_level")
            if isinstance(data.get("guard_level"), int) and "guard_level" not in sender_payload:
                sender_payload["guard_level"] = data.get("guard_level")
            if sender_payload:
                payload["sender"] = sender_payload

            # 接收者信息（被赠送方）
            receiver_payload: Dict[str, Any] = {}
            receive_user_info = data.get("receive_user_info")
            if isinstance(receive_user_info, dict):
                if "uid" in receive_user_info:
                    receiver_payload["uid"] = receive_user_info.get("uid")
                if receive_user_info.get("uname"):
                    receiver_payload["uname"] = receive_user_info.get("uname")
            receiver_uinfo = data.get("receiver_uinfo")
            if isinstance(receiver_uinfo, dict):
                base = receiver_uinfo.get("base") or {}
                if isinstance(base, dict):
                    if base.get("name") and "uname" not in receiver_payload:
                        receiver_payload["uname"] = base.get("name")
                    if base.get("face"):
                        receiver_payload["face"] = base.get("face")
                if isinstance(receiver_uinfo.get("medal"), dict):
                    medal = receiver_uinfo.get("medal")
                    receiver_payload["medal"] = {
                        "name": medal.get("name"),
                        "level": medal.get("level"),
                        "is_light": medal.get("is_light"),
                        "ruid": medal.get("ruid"),
                        "guard_level": medal.get("guard_level")
                    }
                if isinstance(receiver_uinfo.get("guard"), dict):
                    receiver_payload["guard_level"] = receiver_uinfo["guard"].get("level")
                if isinstance(receiver_uinfo.get("wealth"), dict):
                    receiver_payload["wealth_level"] = receiver_uinfo["wealth"].get("level")
                if isinstance(receiver_uinfo.get("uid"), int):
                    receiver_payload["uid"] = receiver_uinfo.get("uid")
            if receiver_payload:
                payload["receiver"] = receiver_payload

            # 事件辅助信息
            for k in [
                "timestamp", "tid", "rnd", "batch_combo_id", "combo_total_coin", "total_coin"
            ]:
                if k in data and data.get(k) is not None:
                    payload[k] = data.get(k)
            # combo_send 里的组合ID
            combo_send = data.get("combo_send")
            if isinstance(combo_send, dict) and combo_send.get("combo_id"):
                payload["combo_id"] = combo_send.get("combo_id")

            # 礼物动画与图标等可视资源
            gift_info = data.get("gift_info")
            if isinstance(gift_info, dict):
                gift_assets: Dict[str, Any] = {}
                for key in ["effect_id", "gif", "webp", "img_basic", "has_imaged_gift"]:
                    if key in gift_info:
                        gift_assets[key] = gift_info.get(key)
                if gift_assets:
                    payload["gift_assets"] = gift_assets

            # 其他视觉/动效标志与资源
            if data.get("tag_image"):
                payload["tag_image"] = data.get("tag_image")
            for k in ["effect", "effect_block", "svga_block", "combo_resources_id"]:
                if k in data and data.get(k) is not None:
                    payload[k] = data.get(k)
            # 面部特效（v2结构）
            face_effect_v2 = data.get("face_effect_v2")
            if isinstance(face_effect_v2, dict):
                payload["face_effect_v2"] = {
                    "id": face_effect_v2.get("id"),
                    "type": face_effect_v2.get("type")
                }
            # 旧的 face_effect_* 字段
            if "face_effect_id" in data:
                payload["face_effect_id"] = data.get("face_effect_id")
            if "face_effect_type" in data:
                payload["face_effect_type"] = data.get("face_effect_type")
            # 标签类资源
            if isinstance(data.get("gift_tag"), list):
                payload["gift_tag"] = data.get("gift_tag")
            
            success, _ = self.api_client.post("money", payload)
            if success:
                logger.info(f"✅ 礼物记录已发送: {uname} 赠送 {gift_name} x{gift_num}")
            else:
                logger.error(f"❌ 礼物记录发送失败: {uname} 赠送 {gift_name} x{gift_num}")
        except Exception as e:
            logger.error(f"❌ 处理礼物消息时发生错误: {e}")
    
    def stop(self) -> None:
        """停止处理器"""
        pass


# 上舰（大航海购买/续费）处理器
class GuardBuyHandler(EventHandler):
    def __init__(self, room_id: int, api_client: APIClient):
        self.room_id = room_id
        self.api_client = api_client

    def handle(self, message: Dict[str, Any]) -> None:
        """处理上舰相关事件（如 GUARD_BUY / USER_TOAST_MSG），上报到 /guard 接口"""
        try:
            uid = None
            username = None
            guard_level = None
            num = None
            price = None
            gift_id = None
            gift_name = None
            start_time = None
            end_time = None

            data = message.get("data", {}) if isinstance(message, dict) else {}

            if isinstance(data, dict):
                # 常见字段（GUARD_BUY）
                uid = data.get("uid") or data.get("user_id")
                username = data.get("username") or data.get("user_name") or data.get("uname")
                guard_level = data.get("guard_level") or data.get("role_level")
                num = data.get("num") or data.get("count")
                price = data.get("price")
                gift_id = data.get("gift_id")
                gift_name = data.get("gift_name") or data.get("role_name")
                start_time = data.get("start_time")
                end_time = data.get("end_time")

                # USER_TOAST_MSG 有时字段在 data.toast_msg/其他位置，尽量兜底
                if not gift_name and isinstance(data.get("toast_msg"), str):
                    gift_name = data.get("toast_msg")

            payload = {
                "room_id": self.room_id,
                "uid": uid,
                "username": username,
                "guard_level": guard_level,
                "count": num,
                "price": price,
                "gift_id": gift_id,
                "gift_name": gift_name,
                "start_time": start_time,
                "end_time": end_time,
                "raw_message": message
            }

            success, _ = self.api_client.post("guard", payload)
            if success:
                logger.info(f"✅ 上报上舰事件成功：uid={uid or '-'} username={username or '-'} level={guard_level} count={num}")
            else:
                logger.error("❌ 上报上舰事件失败 (/guard)")
        except Exception as e:
            logger.error(f"❌ 处理上舰事件时发生错误: {e}")

    def stop(self) -> None:
        pass

# 进场特效（用户进入）处理器
class EntryEffectHandler(EventHandler):
    def __init__(self, room_id: int, api_client: APIClient):
        self.room_id = room_id
        self.api_client = api_client

    def handle(self, message: Dict[str, Any]) -> None:
        """处理 ENTRY_EFFECT（用户进入）事件，转发到 /entry_welcome 接口"""
        try:
            data = message.get("data", {}) if isinstance(message, dict) else {}
            uid = None
            uname = None
            face_url = None
            wealth_level = None
            medal_info: Dict[str, Any] = {}
            guard_level = None
            privilege_type = None

            if isinstance(data, dict):
                # uid、uname、头像
                uid = data.get("uid") or (data.get("uinfo", {}) or {}).get("uid")
                uinfo = data.get("uinfo") or {}
                base = uinfo.get("base") if isinstance(uinfo, dict) else None
                if isinstance(base, dict):
                    uname = base.get("name")
                    face_url = base.get("face")
                if not face_url:
                    face_url = data.get("face")

                # 财富等级
                wealth = uinfo.get("wealth") if isinstance(uinfo, dict) else None
                if isinstance(wealth, dict):
                    wealth_level = wealth.get("level")
                if wealth_level is None and isinstance(data.get("wealthy_info"), dict):
                    wealth_level = data["wealthy_info"].get("level")

                # 勋章信息（牌子 + 等级）
                medal = uinfo.get("medal") if isinstance(uinfo, dict) else None
                if isinstance(medal, dict):
                    medal_info = {
                        "name": medal.get("name"),
                        "level": medal.get("level"),
                        "is_light": medal.get("is_light"),
                        "ruid": medal.get("ruid"),
                        "guard_level": medal.get("guard_level"),
                        "color": medal.get("color"),
                        "color_start": medal.get("color_start"),
                        "color_end": medal.get("color_end"),
                        "color_border": medal.get("color_border"),
                    }

                # 舰长/大航海等级与类型
                guard = uinfo.get("guard") if isinstance(uinfo, dict) else None
                if isinstance(guard, dict):
                    guard_level = guard.get("level")
                privilege_type = data.get("privilege_type")

            # 是否是舰长（guard_level==3 或 privilege_type==3 视为舰长）
            is_captain = (guard_level == 3) or (privilege_type == 3)

            payload: Dict[str, Any] = {
                "room_id": self.room_id,
                "raw_message": message,
                "is_captain": bool(is_captain),
            }
            if uid is not None:
                payload["uid"] = uid
            if uname:
                payload["uname"] = uname
            if face_url:
                payload["face"] = face_url
            if wealth_level is not None:
                payload["wealth_level"] = wealth_level
            if medal_info:
                payload["medal"] = medal_info
            if guard_level is not None:
                payload["guard_level"] = guard_level
            if privilege_type is not None:
                payload["privilege_type"] = privilege_type

            success, _ = self.api_client.post("entry_welcome", payload)
            if success:
                logger.info(
                    f"✅ /entry_welcome 上报成功：uid={uid or '-'} uname={uname or '-'} is_captain={is_captain}"
                )
            else:
                logger.error("❌ 上报 /entry_welcome 失败")
        except Exception as e:
            logger.error(f"❌ 处理 ENTRY_EFFECT 时发生错误: {e}")

    def stop(self) -> None:
        pass

# 直播间列表处理器
class LiveRoomListHandler(EventHandler):
    def __init__(self, room_id: int, api_client: APIClient):
        self.room_id = room_id
        self.api_client = api_client
    
    def handle(self, message: Dict[str, Any]) -> None:
        """处理 STOP_LIVE_ROOM_LIST 消息"""
        payload = {
            "room_id": self.room_id,
            "stop_live_room_list": message.get("data", {})
        }
        
        if self.api_client.post("live_room_spider", payload):
            logger.info("✅ STOP_LIVE_ROOM_LIST 已成功发送")
    
    def stop(self) -> None:
        """停止处理器"""
        pass


# 消息处理工厂
class MessageHandlerFactory:
    @staticmethod
    def create_handler(cmd: str, room_id: int, api_client: APIClient, spider_enabled: bool = False) -> Optional[EventHandler]:
        """根据命令类型创建对应的处理器
        
        Args:
            cmd: 消息命令
            room_id: 房间ID
            api_client: API客户端
            spider_enabled: 是否启用爬虫功能
            
        Returns:
            EventHandler或None: 创建的处理器实例
        """
        # 如果是STOP_LIVE_ROOM_LIST消息但爬虫功能未启用，则不创建处理器
        if cmd == "STOP_LIVE_ROOM_LIST" and not spider_enabled:
            return None
            
        handlers = {
            "DANMU_MSG": DanmakuHandler,
            "SEND_GIFT": GiftHandler,
            "STOP_LIVE_ROOM_LIST": LiveRoomListHandler,
            "ENTRY_EFFECT": EntryEffectHandler,
            "GUARD_BUY": GuardBuyHandler,
            "USER_TOAST_MSG": GuardBuyHandler,
        }
        
        handler_class = handlers.get(cmd)
        if handler_class:
            return handler_class(room_id, api_client)
        return None


# B站消息解析器
class BiliMessageParser:
    def __init__(self, room_id: int, api_base_url: str = API_BASE_URL, spider: bool = False, debug_events: bool = False, on_authenticated=None, only_gift_guard: bool = False):
        self.room_id = room_id
        self.api_client = APIClient(api_base_url)
        self.current_pk_handler = None
        # 确保将spider参数转换为布尔值
        self.spider_enabled = bool(spider)
        self.debug_events = bool(debug_events)
        self.on_authenticated = on_authenticated
        self.only_gift_guard = bool(only_gift_guard)
        
        # 初始化处理器映射
        self.persistent_handlers = {}
        
        # 注册处理器
        if self.spider_enabled:
            self.persistent_handlers["STOP_LIVE_ROOM_LIST"] = LiveRoomListHandler(room_id, self.api_client)
            logger.info("🕷️ 直播间爬虫功能已启用，将监听 STOP_LIVE_ROOM_LIST 消息")
        else:
            logger.info("ℹ️ 直播间爬虫功能未启用")
        
        if self.only_gift_guard:
            logger.info("🎯 仅监听并处理 礼物与上舰 相关事件（SEND_GIFT、GUARD_BUY、USER_TOAST_MSG）")
    
    def parse_message(self, data: bytes) -> None:
        """解析服务器返回的消息"""
        try:
            offset = 0
            while offset < len(data):
                packet_length = int.from_bytes(data[offset:offset + 4], "big")
                header_length = int.from_bytes(data[offset + 4:offset + 6], "big")
                protover = int.from_bytes(data[offset + 6:offset + 8], "big")
                operation = int.from_bytes(data[offset + 8:offset + 12], "big")
                body = data[offset + header_length:offset + packet_length]

                # Debug模式：尽可能打印原始包信息
                if self.debug_events:
                    try:
                        if operation == 5:
                            # 业务消息包
                            preview = body
                            # 在压缩包情况下，body不是JSON，后续分支会解压；这里仅记录头部信息
                            logger.debug(f"🧩 包: proto={protover}, op={operation}, len={packet_length}")
                        elif operation == 3:
                            popularity = int.from_bytes(body, "big")
                            print(f"[DEBUG] 人气值: {popularity}", flush=True)
                        else:
                            logger.debug(f"🧩 包: proto={protover}, op={operation}, len={packet_length}")
                    except Exception:
                        pass

                if protover == 2:
                    decompressed_data = zlib.decompress(body)
                    self.parse_message(decompressed_data)
                elif protover == 3:
                    decompressed_data = brotli.decompress(body)
                    self.parse_message(decompressed_data)
                elif protover in (0, 1):
                    if operation == 5:
                        message = json.loads(body.decode("utf-8"))
                        if self.debug_events:
                            try:
                                # 美化打印整条消息（不做任何过滤）
                                print("[DEBUG] 事件:\n" + json.dumps(message, ensure_ascii=False, indent=2), flush=True)
                            except Exception:
                                # 兜底打印
                                print(f"[DEBUG] 事件: {message}", flush=True)
                        self._handle_message(message)
                    elif operation == 3:
                        popularity = int.from_bytes(body, "big")
                        if self.debug_events:
                            print(f"[DEBUG] 人气值: {popularity}", flush=True)
                    elif operation == 8:
                        # op=8 认证通过
                        if callable(self.on_authenticated):
                            self.on_authenticated()
                        if self.debug_events:
                            print("[DEBUG] 认证成功(op=8)，将启动心跳", flush=True)
                offset += packet_length
        except Exception as e:
            logger.error(f"❌ 消息解析错误: {e}")
    
    def _handle_message(self, message: Dict[str, Any]) -> None:
        """处理解析后的消息"""
        try:
            if isinstance(message, dict):
                cmd = message.get("cmd", "")
                
                # 处理 PK 相关消息
                if cmd == "PK_INFO" or cmd == "PK_BATTLE_PROCESS_NEW":
                    if self.current_pk_handler:
                        self.current_pk_handler.handle(message)
                elif cmd == "PK_BATTLE_START_NEW":
                    logger.info("✅ 收到 PK_BATTLE_START_NEW 消息")
                    battle_type = message["data"].get("battle_type", Constants.PK_TYPE_1)
                    self.current_pk_handler = PKBattleHandler(
                        self.room_id, self.api_client, battle_type
                    )
                elif cmd == "PK_BATTLE_END":
                    logger.info("🛑 收到 PK_BATTLE_END 消息，销毁 PKBattleHandler 实例")
                    if self.current_pk_handler:
                        self.current_pk_handler.stop()
                        self.current_pk_handler = None
                # 对STOP_LIVE_ROOM_LIST消息的特殊处理: 只有当spider_enabled为真时才处理
                elif cmd == "STOP_LIVE_ROOM_LIST":
                    if self.spider_enabled:
                        handler = self.persistent_handlers.get(cmd)
                        if handler:
                            handler.handle(message)
                    else:
                        logger.debug(f"收到STOP_LIVE_ROOM_LIST消息，但爬虫功能未启用，忽略此消息")
                # 处理其他消息
                else:
                    # 如果启用 only_gift_guard，则仅处理礼物与上舰相关事件
                    if self.only_gift_guard:
                        allowed_cmds = {"SEND_GIFT", "GUARD_BUY", "USER_TOAST_MSG"}
                        if cmd not in allowed_cmds:
                            # 在调试模式下打印被过滤的事件类型
                            if self.debug_events:
                                logger.debug(f"[过滤] 已启用 only_gift_guard，忽略事件: {cmd}")
                            return
                    # 检查是否有持久化处理器
                    handler = self.persistent_handlers.get(cmd)
                    
                    # 如果没有持久化处理器，则创建一个临时处理器
                    if not handler and cmd != "":
                        handler = MessageHandlerFactory.create_handler(cmd, self.room_id, self.api_client, self.spider_enabled)
                    
                    # 如果有处理器，则处理消息
                    if handler:
                        handler.handle(message)
        except Exception as e:
            logger.error(f"❌ 处理消息时发生错误: {e}")
