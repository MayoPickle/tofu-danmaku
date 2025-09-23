# main.py

import os
import readline
import atexit
import argparse

from src.bili_danmaku_client import BiliDanmakuClient
from src.room_history import load_history, append_room_history, show_history

# 准备一个专门用于存储"脚本内部输入历史"（并非房间号历史）的文件
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
    parser.add_argument('--spider', action='store_true', help='启用直播间爬虫功能，监听STOP_LIVE_ROOM_LIST消息')
    parser.add_argument('--api', type=str, help='API服务器URL，例如 http://127.0.0.1:8081')
    parser.add_argument('--debug-events', action='store_true', help='调试模式：打印所有收到的事件（不做过滤）')
    parser.add_argument('--cookie', type=str, help='B站 Cookie 字符串（例如 "SESSDATA=...; bili_jct=..."），用于携带登录态')
    parser.add_argument('--login', action='store_true', help='扫码登录B站账号（成功后本次会话携带登录Cookie）；不传则游客')
    parser.add_argument('--debug-ws', action='store_true', help='启用底层WebSocket和网络详细日志（会打印脱敏信息）')
    parser.add_argument('--only-gift-guard', action='store_true', help='仅监听礼物投喂与上舰相关事件（SEND_GIFT、GUARD_BUY、USER_TOAST_MSG），并进行上报')
    return parser.parse_args()

def main():
    # 启动时先加载"脚本内部输入历史"
    load_readline_history()
    # 程序退出时自动保存
    atexit.register(save_readline_history)

    # 解析命令行参数
    args = get_arguments()

    # 如果传入了 --room-id 参数，直接启动
    if args.room_id:
        room_id = args.room_id
        print(f"已通过命令行传入房间号：{room_id}，即将开始连接。")
        
        if args.spider:
            print("🕷️ 直播间爬虫功能已启用")

        # 载入已保存的房间号历史
        history_list = load_history()
        history_ids = [str(h["room_id"]) for h in history_list]

        # 如需扫码登录，优先进行登录获取 Cookie
        cookie_header = args.cookie
        if args.login and not cookie_header:
            from src.login_qrcode import login_with_qrcode
            print("即将弹出二维码（终端打印），请使用B站App扫码登录……")
            cookies, cookie_header = login_with_qrcode(
                persist_path=os.path.join(os.getcwd(), 'bzcookies'),
                timeout_seconds=180
            )
            print("登录完成，开始连接WS…")

        # 启动客户端
        client = BiliDanmakuClient(
            room_id,
            spider=args.spider,
            api_base_url=args.api,
            debug_events=args.debug_events,
            cookie=cookie_header,
            debug_ws=args.debug_ws,
            only_gift_guard=args.only_gift_guard
        )
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

    # 显示爬虫状态
    if args.spider:
        print("🕷️ 直播间爬虫功能已启用")
        
    # 如需扫码登录，优先进行登录获取 Cookie
    cookie_header = args.cookie
    if args.login and not cookie_header:
        from src.login_qrcode import login_with_qrcode
        print("即将弹出二维码（终端打印），请使用B站App扫码登录……")
        cookies, cookie_header = login_with_qrcode(
            persist_path=os.path.join(os.getcwd(), 'bzcookies'),
            timeout_seconds=180
        )
        print("登录完成，开始连接WS…")

    # 启动客户端
    client = BiliDanmakuClient(
        room_id,
        spider=args.spider,
        api_base_url=args.api,
        debug_events=args.debug_events,
        cookie=cookie_header,
        debug_ws=args.debug_ws,
        only_gift_guard=args.only_gift_guard
    )
    client.start()


if __name__ == "__main__":
    main()
