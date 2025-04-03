"""
默认回复配置文件
包含所有预设的回复消息
"""

# 系统消息
SYSTEM_MESSAGES = {
    "startup": "闲鱼自动回复助手已启动",
    "shutdown": "系统正在安全退出...",
    "login_success": "登录成功",
    "login_failed": "登录失败，请重试",
}

# 特殊消息类型的回复
SPECIAL_TYPE_RESPONSES = {
    "image": {
        "wait": "稍等，让我看看哈~",
        "processing": "正在分析图片内容...",
        "success": "图片分析完成",
        "failed": "抱歉，图片处理失败了"
    },
    "voice": "你好这边听不了语音哈，不好意思，能不能发成文字内容",
    "video": "抱歉，暂时无法处理视频内容，请发送文字或图片",
    "location": "抱歉，暂时无法处理位置信息"
}

# 错误消息
ERROR_MESSAGES = {
    "token_invalid": "登录信息已失效，请重新登录",
    "network_error": "网络连接错误，正在重试...",
    "api_error": "API调用失败，请稍后重试",
    "cookie_invalid": "Cookie无效或已过期",
    "parse_error": "消息解析失败"
}

# 提示消息
PROMPT_MESSAGES = {
    "cookie_input": "请从浏览器F12中复制完整的cookie文本",
    "login_options": "\n登录方式选择：\n1. 使用上次登录信息\n2. 扫码登录（推荐）\n3. 手动输入Cookie\n4. 退出程序",
    "cookie_update": "\nToken验证失败，请选择更新方式：\n1. 扫码登录\n2. 手动输入Cookie\n3. 退出程序"
}

def get_response(category, key, **kwargs):
    """
    获取对应的回复消息
    :param category: 消息类别（system/special/error/prompt）
    :param key: 消息键值
    :param kwargs: 格式化参数
    :return: 格式化后的消息
    """
    categories = {
        "system": SYSTEM_MESSAGES,
        "special": SPECIAL_TYPE_RESPONSES,
        "error": ERROR_MESSAGES,
        "prompt": PROMPT_MESSAGES
    }
    
    if category not in categories:
        return None
        
    message = categories[category].get(key)
    if not message:
        return None
        
    # 如果是嵌套字典（比如image的多个状态），直接返回
    if isinstance(message, dict):
        return message.get(kwargs.get('sub_key', ''))
        
    # 尝试格式化消息
    try:
        return message.format(**kwargs) if kwargs else message
    except:
        return message 