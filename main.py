# main.py

import os
import readline
import atexit
import argparse

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

def get_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="Bili Danmaku Client")
    parser.add_argument('--room-id', type=int, help='直接传入房间号启动，不显示房间历史列表')
    return parser.parse_args()

def main():
    # 启动时先加载“脚本内部输入历史”
    load_readline_history()
    # 程序退出时自动保存
    atexit.register(save_readline_history)

    # 解析命令行参数
    args = get_arguments()

    # 如果传入了 --room-id 参数，直接启动
    if args.room_id:
        room_id = args.room_id
        print(f"已通过命令行传入房间号：{room_id}，即将开始连接。")

        # 载入已保存的房间号历史
        history_list = load_history()
        history_ids = [str(h["room_id"]) for h in history_list]

        # 启动客户端
        client = BiliDanmakuClient(room_id)
        client.start()
        return  # 启动后直接退出函数

    # 如果未传入房间号参数，按正常流程执行
    print("===== Bili Danmaku Client =====")
    print("历史记录如下：")
    print(show_history())
    print("\n请输入房间号（可以用上下箭头选择历史输入）：")

    # 载入已保存的房间号历史
    history_list = load_history()
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
