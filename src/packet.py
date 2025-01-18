import json
import struct

def create_handshake_packet(self):
    """生成认证包"""
    payload = {
        "uid": 0,          # 0 表示游客登录
        "roomid": self.room_id,
        "protover": 3,     # 使用 brotli 压缩
        "platform": "web",
        "type": 2,
        "key": self.token  # 动态填入 token
    }
    payload_bytes = json.dumps(payload).encode("utf-8")
    header = struct.pack('>IHHII', len(payload_bytes) + 16, 16, 1, 7, 1)
    return header + payload_bytes


def create_heartbeat_packet():
    """生成心跳包"""
    return struct.pack('>IHHII', 16, 16, 1, 2, 1)

