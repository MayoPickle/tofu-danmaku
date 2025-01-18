import readline  # readline 用于支持在终端里上下箭头查看历史输入（Unix 系统）
# 如果你在 Windows 上无法用上下键，需要安装 pyreadline 或者其他替代方案

from src.bili_danmaku_client import BiliDanmakuClient
from src.room_history import append_room_history, show_history


def main():
    print("===== Bili Danmaku Client =====")
    print("历史记录如下：")
    print(show_history())
    print("\n请输入房间号（可以用上下箭头选择历史输入）：")

    room_id_str = input("> ").strip()
    if not room_id_str.isdigit():
        print("输入的房间号不是数字，程序退出。")
        return

    room_id = int(room_id_str)

    note = input("请给这个房间ID加个备注(可选，直接回车跳过)：").strip()

    # 把新的房间号及备注加入/更新到历史记录
    append_room_history(room_id, note if note else "")

    client = BiliDanmakuClient(room_id)
    client.start()


if __name__ == "__main__":
    main()

