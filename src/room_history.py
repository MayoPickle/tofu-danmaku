import os
import json

HISTORY_FILE = "history.json"


def load_history():
    """加载历史记录(房间号和备注)"""
    if not os.path.exists(HISTORY_FILE):
        return []
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []


def save_history(history_list):
    """保存历史记录到文件"""
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history_list, f, ensure_ascii=False, indent=2)


def append_room_history(room_id, note):
    """向历史记录里追加新的房间号"""
    history_list = load_history()
    # 简单去重逻辑：如果已经存在同样的 room_id，就更新备注，否则追加
    for item in history_list:
        if item["room_id"] == room_id:
            item["note"] = note
            break
    else:
        history_list.append({"room_id": room_id, "note": note})
    save_history(history_list)


def show_history():
    """返回一个格式化后的历史信息字符串，用于展示给用户"""
    history_list = load_history()
    if not history_list:
        return "暂无历史记录"
    lines = []
    for idx, item in enumerate(history_list, start=1):
        lines.append(f"{idx}. 房间号: {item['room_id']}, 备注: {item['note']}")
    return "\n".join(lines)

