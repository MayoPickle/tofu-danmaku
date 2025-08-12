import json
import struct

def create_handshake_packet(self):
    """生成认证包"""
    # 如果有登录UID则带上；否则为0
    try:
        uid = int(getattr(self, 'user_uid', 0) or 0)
    except Exception:
        uid = 0
    buvid = getattr(self, 'buvid3', '') or ''

    payload = {
        "uid": uid,
        "roomid": self.room_id,
        "protover": 3,
        "platform": "web",
        "type": 2,
        "key": self.token,
        **({"buvid": buvid} if buvid else {}),
    }
    payload_bytes = json.dumps(payload).encode("utf-8")
    header = struct.pack('>IHHII', len(payload_bytes) + 16, 16, 1, 7, 1)
    return header + payload_bytes


def create_heartbeat_packet():
    """生成心跳包"""
    return struct.pack('>IHHII', 16, 16, 1, 2, 1)

