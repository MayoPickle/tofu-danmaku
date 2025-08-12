import json
import os
import time
import logging
import requests
from typing import Dict, Tuple, Optional

logger = logging.getLogger(__name__)


API = {
    "qrcode": {
        "generate": "https://passport.bilibili.com/x/passport-login/web/qrcode/generate",
        "poll": "https://passport.bilibili.com/x/passport-login/web/qrcode/poll",
    },
    "nav": "https://api.bilibili.com/x/web-interface/nav",
}

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://www.bilibili.com/",
}

PASSPORT_HEADERS = {
    "User-Agent": DEFAULT_HEADERS["User-Agent"],
    "Host": "passport.bilibili.com",
    "Referer": "https://passport.bilibili.com/login",
}


def _print_qr_to_terminal(url: str) -> None:
    try:
        # 纯依赖最小化：不强制 Pillow/tkinter，直接终端打印二维码
        import qrcode

        qr = qrcode.QRCode(border=1)
        qr.add_data(url)
        qr.make(fit=True)
        matrix = qr.get_matrix()
        # 使用全块字符以便在终端显示更清晰
        black = "\u2588\u2588"
        white = "  "
        lines = []
        for row in matrix:
            line = "".join(black if cell else white for cell in row)
            lines.append(line)
        print("\n".join(lines), flush=True)
    except Exception as e:
        logger.warning(f"无法在终端打印二维码，将直接输出登录链接，请自行在手机扫码打开: {e}")
        print(f"请用手机扫码打开以下链接完成登录: {url}", flush=True)


def _cookie_jar_to_dict(session: requests.Session) -> Dict[str, str]:
    cookies: Dict[str, str] = {}
    for c in session.cookies:
        cookies[c.name] = c.value
    return cookies


def _dict_to_cookie_header(cookies: Dict[str, str]) -> str:
    return "; ".join([f"{k}={v}" for k, v in cookies.items()])


def load_cookie_if_valid(persist_path: str) -> Optional[Tuple[Dict[str, str], str]]:
    """尝试从持久化文件加载并校验 Cookie；有效则返回(cookies_dict, header_str)，否则返回 None"""
    try:
        import http.cookiejar as cookielib
        session = requests.Session()
        session.headers.update(DEFAULT_HEADERS)
        session.cookies = cookielib.LWPCookieJar(filename=persist_path)
        if not os.path.exists(persist_path):
            return None
        session.cookies.load(ignore_discard=True, ignore_expires=True)
        nav = session.get(API["nav"], headers=DEFAULT_HEADERS, timeout=10).json()
        if nav.get("code") == 0:
            uname = nav.get("data", {}).get("uname", "")
            print(f"检测到本地Cookie有效：{uname}（将复用登录态）")
            cookies = _cookie_jar_to_dict(session)
            return cookies, _dict_to_cookie_header(cookies)
    except Exception:
        return None
    return None


def login_with_qrcode(persist_path: Optional[str] = None, timeout_seconds: int = 180) -> Tuple[Dict[str, str], str]:
    """终端二维码登录，返回 cookies dict 和可直接用于请求头的 Cookie 字符串。

    Args:
        persist_path: 可选，cookies 持久化文件路径（LWPCookieJar）。
        timeout_seconds: 登录超时时间。

    Returns:
        (cookies_dict, cookie_header_string)
    """
    session = requests.Session()
    session.headers.update(DEFAULT_HEADERS)

    # 可选持久化
    if persist_path:
        try:
            import http.cookiejar as cookielib

            session.cookies = cookielib.LWPCookieJar(filename=persist_path)
            if os.path.exists(persist_path):
                session.cookies.load(ignore_discard=True, ignore_expires=True)
        except Exception as e:
            logger.warning(f"初始化 Cookie 持久化失败: {e}")

    # 如果已有持久化 Cookie 且有效，直接复用
    if persist_path and os.path.exists(persist_path):
        loaded = load_cookie_if_valid(persist_path)
        if loaded:
            return loaded

    # Step1: 获取二维码与 key
    resp = session.get(API["qrcode"]["generate"], headers=DEFAULT_HEADERS, timeout=10)
    resp.raise_for_status()
    data = resp.json().get("data", {})
    qrcode_key = data.get("qrcode_key")
    qrcode_url = data.get("url")
    if not qrcode_key or not qrcode_url:
        raise RuntimeError("获取二维码失败：返回缺少 qrcode_key 或 url")

    print("请使用 Bilibili App 扫码登录：")
    _print_qr_to_terminal(qrcode_url)

    # Step2: 轮询登录状态
    start = time.time()
    last_status = None
    while True:
        if time.time() - start > timeout_seconds:
            raise TimeoutError("二维码登录超时，请重试")
        try:
            poll = session.get(
                API["qrcode"]["poll"],
                params={"qrcode_key": qrcode_key},
                headers=PASSPORT_HEADERS,
                timeout=10,
            )
            j = poll.json()
        except Exception:
            time.sleep(1.5)
            continue

        code = j.get("data", {}).get("code")
        if code != last_status:
            last_status = code
            if code == 86101:
                print("二维码未失效，等待扫码...", flush=True)
            elif code == 86090:
                print("已扫码，等待确认...", flush=True)
            elif code == 86038:
                print("二维码已过期，正在刷新...", flush=True)
        
        # 成功：返回数据中包含跳转 URL，用于设置登录 Cookie
        if isinstance(j.get("data"), dict) and j["data"].get("url"):
            redirect_url = j["data"]["url"]
            # 访问该地址以写入 cookie
            session.get(redirect_url, headers=DEFAULT_HEADERS, timeout=10)
            # 校验登录
            nav = session.get(API["nav"], headers=DEFAULT_HEADERS, timeout=10).json()
            if nav.get("code") == 0:
                uname = nav.get("data", {}).get("uname", "")
                print(f"登录成功：{uname}")
            else:
                print("登录完成，但校验失败，可能受风控影响。")

            if persist_path:
                try:
                    # 尝试保存持久化
                    session.cookies.save(ignore_discard=True, ignore_expires=True)
                except Exception:
                    pass

            cookies = _cookie_jar_to_dict(session)
            return cookies, _dict_to_cookie_header(cookies)

        time.sleep(2)


