# main.py

import os
import readline
import atexit

from src.bili_danmaku_client import BiliDanmakuClient
from src.room_history import load_history, append_room_history, show_history

# 准备一个专门用于存储“脚本内部输入历史”（并非房间号历史）的文件
READLINE_HISTORY = ".danmaku_input_history"

def load_readline_history():
    """如果有历史文件，则载入到当前会话"""
    if os.path.exists(READLINE_HISTORY):
        readline.read_history_file(READLINE_HISTORY)

def save_readline_history():
    """把当前会话的输入历史写回文件"""
    readline.write_history_file(READLINE_HISTORY)

def main():
    # 启动时先加载“脚本内部输入历史”
    load_readline_history()
    # 程序退出时自动保存
    atexit.register(save_readline_history)

    print("===== Bili Danmaku Client =====")
    print("历史记录如下：")
    print(show_history())
    print("\n请输入房间号（可以用上下箭头选择历史输入）：")

    # 载入已保存的房间号历史
    history_list = load_history()
    # 提前收集所有历史中的房间号，方便后续判断
    history_ids = [str(h["room_id"]) for h in history_list]

    # 把旧的房间号加到当前 readline 历史，方便用上下箭头选择
    for h_id in history_ids:
        readline.add_history(h_id)

    # 获取用户输入的房间号
    room_id_str = input("> ").strip()
    # 判断输入是否合法
    if not room_id_str.isdigit():
        print("输入的房间号不是数字，程序退出。")
        return
    room_id = int(room_id_str)

    # 如果这个房间号不在历史里，才询问备注并保存
    if room_id_str not in history_ids:
        note = input("请给这个房间ID加个备注(可选，直接回车跳过)：").strip()
        append_room_history(room_id, note if note else "")

    # 启动客户端
    client = BiliDanmakuClient(room_id)
    client.start()


if __name__ == "__main__":
    main()
