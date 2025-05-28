import hashlib
from urllib.parse import urlencode, quote
from collections import OrderedDict

# Mixin key encoding table
MIXIN_KEY_ENC_TAB = [
    46, 47, 18, 2, 53, 8, 23, 32, 15, 50,
    10, 31, 58, 3, 45, 35, 27, 43, 5, 49,
    33, 9, 42, 19, 29, 28, 14, 39, 12, 38,
    41, 13, 37, 48, 7, 16, 24, 55, 40, 61,
    26, 17, 0, 1, 60, 51, 30, 4, 22, 25,
    54, 21, 56, 59, 6, 63, 57, 62, 11, 36,
    20, 34, 44, 52
]

def get_mixin_key(orig):
    """对 imgKey 和 subKey 进行字符顺序打乱编码"""
    temp = []
    for n in MIXIN_KEY_ENC_TAB:
        if n < len(orig):
            temp.append(orig[n])
    return ''.join(temp)[:32]

def encode_wbi(params, img_key, sub_key):
    """
    为请求参数进行 WBI 签名
    
    Args:
        params: 请求参数字典
        img_key: 从用户导航信息中获取的 img_url 的文件名（不含扩展名）
        sub_key: 从用户导航信息中获取的 sub_url 的文件名（不含扩展名）
    
    Returns:
        包含 w_rid 签名的新参数字典
    """
    # 获取 mixin key
    mixin_key = get_mixin_key(img_key + sub_key)
    
    # 按照 key 排序
    sorted_params = OrderedDict(sorted(params.items()))
    
    # 构建查询字符串（不进行 URL 编码）
    query_parts = []
    for k, v in sorted_params.items():
        query_parts.append(f"{k}={v}")
    query = "&".join(query_parts)
    
    # 计算 w_rid
    wbi_sign = hashlib.md5((query + mixin_key).encode()).hexdigest()
    
    # 返回新的参数字典
    new_params = params.copy()
    new_params['w_rid'] = wbi_sign
    
    return new_params

def get_wbi_sign(params, img_key, sub_key):
    """
    生成 WBI 签名（保持向后兼容）
    
    Args:
        params: 请求参数字典
        img_key: 从用户导航信息中获取的 img_url 的文件名（不含扩展名）
        sub_key: 从用户导航信息中获取的 sub_url 的文件名（不含扩展名）
    
    Returns:
        WBI 签名字符串
    """
    # 获取 mixin key
    mixin_key = get_mixin_key(img_key + sub_key)
    
    # 按照 key 排序
    sorted_params = OrderedDict(sorted(params.items()))
    
    # 构建查询字符串（不进行 URL 编码）
    query_parts = []
    for k, v in sorted_params.items():
        query_parts.append(f"{k}={v}")
    query = "&".join(query_parts)
    
    # 计算 MD5
    wbi_sign = hashlib.md5((query + mixin_key).encode()).hexdigest()
    
    return wbi_sign

def extract_key_from_url(url):
    """从 URL 中提取文件名（不含扩展名）"""
    if not url:
        return ""
    # 获取最后一个 '/' 之后的部分
    filename = url.split('/')[-1]
    # 去掉扩展名
    return filename.split('.')[0] 