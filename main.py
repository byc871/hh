import base64
import json
import asyncio
import time
import os
import sys
import signal
import websockets
from loguru import logger
from dotenv import load_dotenv
from XianyuApis import XianyuApis
from cookie_manager import get_and_inject_cookies, CookieManager
from cookie_injector import CookieInjector

from utils.xianyu_utils import generate_mid, generate_uuid, trans_cookies, generate_device_id, decrypt
from XianyuAgent import XianyuReplyBot
from context_manager import ChatContextManager
from image_processor import ImageProcessor
from default_responses import get_response

# 全局变量
app = None

class ConfigManager:
    """配置管理类"""
    def __init__(self):
        self.env_path = '.env'
        self.load_config()
    
    def load_config(self):
        """加载配置"""
        load_dotenv()
        self.cookies_str = os.getenv("COOKIES_STR")
    
    def clear_cookies(self):
        """清除cookie信息"""
        try:
            if os.path.exists(self.env_path):
                with open(self.env_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                
                with open(self.env_path, 'w', encoding='utf-8') as f:
                    for line in lines:
                        if not line.startswith('COOKIES_STR='):
                            f.write(line)
                logger.info("已清除上次的cookie信息")
        except Exception as e:
            logger.error(f"清除.env文件时出错: {e}")

class LoginManager:
    """登录管理类"""
    def __init__(self, config_manager):
        self.config = config_manager
        self.cookie_manager = CookieManager()
        self.xianyu = XianyuApis()
    
    async def validate_token(self, cookies_str):
        """验证token"""
        try:
            cookies = trans_cookies(cookies_str)
            device_id = generate_device_id(cookies['unb'])
            token_response = self.xianyu.get_token(cookies, device_id)
            return token_response and 'data' in token_response and 'accessToken' in token_response['data']
        except Exception as e:
            logger.error(f"Token验证失败: {e}")
            return False
    
    async def handle_login(self, choice):
        """处理登录"""
        if choice == '1':
            if not self.config.cookies_str:
                logger.error("未找到COOKIES_STR环境变量")
                return None
            return self.config.cookies_str
            
        self.config.clear_cookies()
        
        if choice == '2':
            cookies_str = get_and_inject_cookies()
            if not cookies_str:
                logger.error("获取cookies失败")
                return None
            return cookies_str
            
        elif choice == '3':
            cookie_str = self.cookie_manager.get_manual_cookies()
            if not cookie_str:
                logger.error("获取cookie文本失败")
                return None
                
            if not self.cookie_manager.inject_cookies(cookie_str):
                logger.error("注入cookie失败")
                return None
                
            self.config.load_config()
            if not self.config.cookies_str:
                logger.error("未找到更新后的COOKIES_STR环境变量")
                return None
            return self.config.cookies_str
            
        return None

class XianyuLive:
    def __init__(self, cookies_str):
        self.xianyu = XianyuApis()
        self.base_url = 'wss://wss-goofish.dingtalk.com/'
        self.cookies_str = cookies_str
        self.cookies = trans_cookies(cookies_str)
        self.myid = self.cookies['unb']
        self.device_id = generate_device_id(self.myid)
        self.context_manager = ChatContextManager()
        self.bot = XianyuReplyBot()
        
        # 从XianyuReplyBot获取图片提示词
        self.image_processor = ImageProcessor(image_prompt=self.bot.image_prompt)
        
        # 心跳相关配置
        self.heartbeat_interval = 15  # 心跳间隔15秒
        self.heartbeat_timeout = 5    # 心跳超时5秒
        self.last_heartbeat_time = 0
        self.last_heartbeat_response = 0
        self.heartbeat_task = None
        self.ws = None

    async def send_msg(self, ws, cid, toid, text):
        text = {
            "contentType": 1,
            "text": {
                "text": text
            }
        }
        text_base64 = str(base64.b64encode(json.dumps(text).encode('utf-8')), 'utf-8')
        msg = {
            "lwp": "/r/MessageSend/sendByReceiverScope",
            "headers": {
                "mid": generate_mid()
            },
            "body": [
                {
                    "uuid": generate_uuid(),
                    "cid": f"{cid}@goofish",
                    "conversationType": 1,
                    "content": {
                        "contentType": 101,
                        "custom": {
                            "type": 1,
                            "data": text_base64
                        }
                    },
                    "redPointPolicy": 0,
                    "extension": {
                        "extJson": "{}"
                    },
                    "ctx": {
                        "appVersion": "1.0",
                        "platform": "web"
                    },
                    "mtags": {},
                    "msgReadStatusSetting": 1
                },
                {
                    "actualReceivers": [
                        f"{toid}@goofish",
                        f"{self.myid}@goofish"
                    ]
                }
            ]
        }
        await ws.send(json.dumps(msg))

    async def init(self, ws):
        token = self.xianyu.get_token(self.cookies, self.device_id)['data']['accessToken']
        msg = {
            "lwp": "/reg",
            "headers": {
                "cache-header": "app-key token ua wv",
                "app-key": "444e9908a51d1cb236a27862abc769c9",
                "token": token,
                "ua": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36 DingTalk(2.1.5) OS(Windows/10) Browser(Chrome/133.0.0.0) DingWeb/2.1.5 IMPaaS DingWeb/2.1.5",
                "dt": "j",
                "wv": "im:3,au:3,sy:6",
                "sync": "0,0;0;0;",
                "did": self.device_id,
                "mid": generate_mid()
            }
        }
        await ws.send(json.dumps(msg))
        # 等待一段时间，确保连接注册完成
        await asyncio.sleep(1)
        msg = {"lwp": "/r/SyncStatus/ackDiff", "headers": {"mid": "5701741704675979 0"}, "body": [
            {"pipeline": "sync", "tooLong2Tag": "PNM,1", "channel": "sync", "topic": "sync", "highPts": 0,
             "pts": int(time.time() * 1000) * 1000, "seq": 0, "timestamp": int(time.time() * 1000)}]}
        await ws.send(json.dumps(msg))
        
        # 显示当前登录用户ID
        logger.info(f"当前登录用户ID: {self.myid}")
            
        logger.info('连接注册完成')

    def is_chat_message(self, message):
        """判断是否为用户聊天消息"""
        try:
            return (
                isinstance(message, dict) 
                and "1" in message 
                and isinstance(message["1"], dict)  # 确保是字典类型
                and "10" in message["1"]
                and isinstance(message["1"]["10"], dict)  # 确保是字典类型
                and "reminderContent" in message["1"]["10"]
            )
        except Exception:
            return False

    def is_image_message(self, message):
        """判断是否为图片消息"""
        try:
            return (
                isinstance(message, dict)
                and "1" in message
                and isinstance(message["1"], dict)
                and "6" in message["1"]
                and isinstance(message["1"]["6"], dict)
                and "3" in message["1"]["6"]
                and isinstance(message["1"]["6"]["3"], dict)
                and "5" in message["1"]["6"]["3"]
            )
        except Exception:
            return False

    def extract_image_info(self, message):
        """提取图片信息"""
        try:
            image_data = json.loads(message["1"]["6"]["3"]["5"])
            if "image" in image_data and "pics" in image_data["image"]:
                image_info = image_data["image"]["pics"][0]
                return {
                    "url": image_info["url"],
                    "width": image_info["width"],
                    "height": image_info["height"],
                    "type": image_info["type"]
                }
        except Exception as e:
            logger.error(f"提取图片信息失败: {e}")
        return None

    def is_sync_package(self, message_data):
        """判断是否为同步包消息"""
        try:
            return (
                isinstance(message_data, dict)
                and "body" in message_data
                and "syncPushPackage" in message_data["body"]
                and "data" in message_data["body"]["syncPushPackage"]
                and len(message_data["body"]["syncPushPackage"]["data"]) > 0
            )
        except Exception:
            return False

    def is_typing_status(self, message):
        """判断是否为用户正在输入状态消息"""
        try:
            return (
                isinstance(message, dict)
                and "1" in message
                and isinstance(message["1"], list)
                and len(message["1"]) > 0
                and isinstance(message["1"][0], dict)
                and "1" in message["1"][0]
                and isinstance(message["1"][0]["1"], str)
                and "@goofish" in message["1"][0]["1"]
            )
        except Exception:
            return False

    async def handle_message(self, message_data, websocket):
        """处理所有类型的消息"""
        try:
            try:
                message = message_data
                ack = {
                    "code": 200,
                    "headers": {
                        "mid": message["headers"]["mid"] if "mid" in message["headers"] else generate_mid(),
                        "sid": message["headers"]["sid"] if "sid" in message["headers"] else '',
                    }
                }
                if 'app-key' in message["headers"]:
                    ack["headers"]["app-key"] = message["headers"]["app-key"]
                if 'ua' in message["headers"]:
                    ack["headers"]["ua"] = message["headers"]["ua"]
                if 'dt' in message["headers"]:
                    ack["headers"]["dt"] = message["headers"]["dt"]
                await websocket.send(json.dumps(ack))
            except Exception as e:
                pass

            # 如果不是同步包消息，直接返回
            if not self.is_sync_package(message_data):
                return

            # 获取并解密数据
            sync_data = message_data["body"]["syncPushPackage"]["data"][0]
            
            # 检查是否有必要的字段
            if "data" not in sync_data:
                return

            # 解密数据
            try:
                data = sync_data["data"]
                try:
                    data = base64.b64decode(data).decode("utf-8")
                    data = json.loads(data)
                    message = data
                except Exception as e:
                    decrypted_data = decrypt(data)
                    message = json.loads(decrypted_data)
            except Exception as e:
                logger.error(f"消息解密失败: {e}")
                return

            # 检查消息类型
            message_type = self.image_processor.get_message_type(message)
            if message_type != "正常消息":
                # 获取用户信息
                send_user_name = message["1"]["10"]["reminderTitle"]
                send_user_id = message["1"]["10"]["senderUserId"]
                cid = message["1"]["2"].split('@')[0]
                
                # 处理语音消息
                if message_type == "语音":
                    response = get_response("special", "voice")
                    await self.send_msg(websocket, cid, send_user_id, response)
                    logger.info(f"已回复语音消息: {response}")
                    return
                
                if message_type == "图片":
                    # 立即发送等待消息
                    wait_msg = get_response("special", "image", sub_key="wait")
                    wait_task = asyncio.create_task(self.send_msg(websocket, cid, send_user_id, wait_msg))
                    logger.info(f"正在发送等待消息: {wait_msg}")
                    
                    # 获取商品信息
                    url_info = message["1"]["10"]["reminderUrl"]
                    item_id = url_info.split("itemId=")[1].split("&")[0] if "itemId=" in url_info else None
                    
                    # 确保等待消息已发送
                    await wait_task
                    logger.info("等待消息已发送")
                    
                    if item_id:
                        self.context_manager.add_message(send_user_id, item_id, "assistant", wait_msg)
                    
                    image_info = self.extract_image_info(message)
                    if image_info:
                        # 处理图片
                        image_description = self.image_processor.process_image(image_info["url"])
                        if image_description:
                            logger.info(f"图片描述: {image_description}")
                            
                            if item_id:
                                # 异步获取商品信息
                                try:
                                    item_info = self.xianyu.get_item_info(self.cookies, item_id)['data']['itemDO']
                                    # 构建商品描述
                                    item_description = []
                                    if 'desc' in item_info and item_info['desc']:
                                        item_description.append(f"商品描述: {item_info['desc']}")
                                    if 'soldPrice' in item_info:
                                        item_description.append(f"当前售价: {str(item_info['soldPrice'])}元")
                                    if 'title' in item_info and item_info['title']:
                                        item_description.append(f"商品标题: {item_info['title']}")
                                    if 'categoryName' in item_info and item_info['categoryName']:
                                        item_description.append(f"商品分类: {item_info['categoryName']}")
                                    
                                    item_description = "; ".join(item_description)
                                    if not item_description:
                                        item_description = "无法获取商品信息"
                                except Exception as e:
                                    logger.error(f"获取商品信息失败: {e}")
                                    item_description = "无法获取商品信息"
                                
                                # 将图片描述添加到上下文
                                self.context_manager.add_message(send_user_id, item_id, "user", f"[图片] {image_description}")
                                
                                # 获取完整的对话上下文
                                context = self.context_manager.get_context(send_user_id, item_id)
                                
                                # 生成回复
                                bot_reply = self.bot.generate_reply(
                                    f"这是一张图片，内容是：{image_description}",
                                    item_description,
                                    context=context
                                )
                                
                                # 添加机器人回复到上下文
                                self.context_manager.add_message(send_user_id, item_id, "assistant", bot_reply)
                                
                                logger.info(f"机器人回复: {bot_reply}")
                                await self.send_msg(websocket, cid, send_user_id, bot_reply)
                return

            # 处理文本消息
            if not self.is_chat_message(message):
                return

            create_time = int(message["1"]["5"])
            send_user_name = message["1"]["10"]["reminderTitle"]
            send_user_id = message["1"]["10"]["senderUserId"]
            send_message = message["1"]["10"]["reminderContent"]
            
            # 时效性验证（过滤5分钟前消息）
            if (time.time() * 1000 - create_time) > 300000:
                return
                
            # 修改：过滤自己发送的消息
            if send_user_id == self.myid:
                logger.debug(f"忽略自己发送的消息: {send_message}")
                return
                
            url_info = message["1"]["10"]["reminderUrl"]
            item_id = url_info.split("itemId=")[1].split("&")[0] if "itemId=" in url_info else None
            
            if not item_id:
                logger.warning(f"消息中未找到商品ID: {send_message}")
                return
                
            try:
                item_info = self.xianyu.get_item_info(self.cookies, item_id)['data']['itemDO']
                # 构建商品描述，包含所有可用信息
                item_description = []
                if 'desc' in item_info and item_info['desc']:
                    item_description.append(f"商品描述: {item_info['desc']}")
                if 'soldPrice' in item_info:
                    item_description.append(f"当前售价: {str(item_info['soldPrice'])}元")
                if 'title' in item_info and item_info['title']:
                    item_description.append(f"商品标题: {item_info['title']}")
                if 'categoryName' in item_info and item_info['categoryName']:
                    item_description.append(f"商品分类: {item_info['categoryName']}")
                
                item_description = "; ".join(item_description)
                if not item_description:
                    item_description = "无法获取商品信息"
                    
            except Exception as e:
                logger.error(f"获取商品信息失败: {e}")
                item_description = "无法获取商品信息"
            
            logger.info(f"收到用户消息 - 用户: {send_user_name}, 消息: {send_message}")
            
            # 添加用户消息到上下文
            self.context_manager.add_message(send_user_id, item_id, "user", send_message)
            
            # 获取完整的对话上下文
            context = self.context_manager.get_context(send_user_id, item_id)
            
            # 生成回复
            bot_reply = self.bot.generate_reply(
                send_message,
                item_description,
                context=context
            )
            
            # 检查是否为价格意图，如果是则增加议价次数
            if self.bot.last_intent == "price":
                self.context_manager.increment_bargain_count(send_user_id, item_id)
                bargain_count = self.context_manager.get_bargain_count(send_user_id, item_id)
                logger.info(f"用户 {send_user_name} 对商品 {item_id} 的议价次数: {bargain_count}")
            
            # 添加机器人回复到上下文
            self.context_manager.add_message(send_user_id, item_id, "assistant", bot_reply)
            
            logger.info(f"机器人回复: {bot_reply}")
            cid = message["1"]["2"].split('@')[0]
            await self.send_msg(websocket, cid, send_user_id, bot_reply)
            
        except Exception as e:
            logger.error(f"处理消息时发生错误: {str(e)}")

    async def send_heartbeat(self, ws):
        """发送心跳包并等待响应"""
        try:
            heartbeat_mid = generate_mid()
            heartbeat_msg = {
                "lwp": "/!",
                "headers": {
                    "mid": heartbeat_mid
                }
            }
            await ws.send(json.dumps(heartbeat_msg))
            self.last_heartbeat_time = time.time()
            logger.debug("心跳包已发送")
            return heartbeat_mid
        except Exception as e:
            logger.error(f"发送心跳包失败: {e}")
            raise

    async def heartbeat_loop(self, ws):
        """心跳维护循环"""
        while True:
            try:
                current_time = time.time()
                
                # 检查是否需要发送心跳
                if current_time - self.last_heartbeat_time >= self.heartbeat_interval:
                    await self.send_heartbeat(ws)
                
                # 检查上次心跳响应时间，如果超时则认为连接已断开
                if (current_time - self.last_heartbeat_response) > (self.heartbeat_interval + self.heartbeat_timeout):
                    logger.warning("心跳响应超时，可能连接已断开")
                    break
                
                await asyncio.sleep(1)
            except Exception as e:
                logger.error(f"心跳循环出错: {e}")
                break

    async def handle_heartbeat_response(self, message_data):
        """处理心跳响应"""
        try:
            if (
                isinstance(message_data, dict)
                and "headers" in message_data
                and "mid" in message_data["headers"]
                and "code" in message_data
                and message_data["code"] == 200
            ):
                self.last_heartbeat_response = time.time()
                logger.debug("收到心跳响应")
                return True
        except Exception as e:
            logger.error(f"处理心跳响应出错: {e}")
        return False

    async def main(self):
        while True:
            try:
                headers = {
                    "Cookie": self.cookies_str,
                    "Host": "wss-goofish.dingtalk.com",
                    "Connection": "Upgrade",
                    "Pragma": "no-cache",
                    "Cache-Control": "no-cache",
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
                    "Origin": "https://www.goofish.com",
                    "Accept-Encoding": "gzip, deflate, br, zstd",
                    "Accept-Language": "zh-CN,zh;q=0.9",
                }

                async with websockets.connect(self.base_url, extra_headers=headers) as websocket:
                    self.ws = websocket
                    await self.init(websocket)
                    
                    # 初始化心跳时间
                    self.last_heartbeat_time = time.time()
                    self.last_heartbeat_response = time.time()
                    
                    # 启动心跳任务
                    self.heartbeat_task = asyncio.create_task(self.heartbeat_loop(websocket))
                    
                    async for message in websocket:
                        try:
                            message_data = json.loads(message)
                            
                            # 处理心跳响应
                            if await self.handle_heartbeat_response(message_data):
                                continue
                            
                            # 发送通用ACK响应
                            if "headers" in message_data and "mid" in message_data["headers"]:
                                ack = {
                                    "code": 200,
                                    "headers": {
                                        "mid": message_data["headers"]["mid"],
                                        "sid": message_data["headers"].get("sid", "")
                                    }
                                }
                                # 复制其他可能的header字段
                                for key in ["app-key", "ua", "dt"]:
                                    if key in message_data["headers"]:
                                        ack["headers"][key] = message_data["headers"][key]
                                await websocket.send(json.dumps(ack))
                            
                            # 处理其他消息
                            await self.handle_message(message_data, websocket)
                                
                        except json.JSONDecodeError:
                            logger.error("消息解析失败")
                        except Exception as e:
                            logger.error(f"处理消息时发生错误: {str(e)}")
                            logger.debug(f"原始消息: {message}")

            except websockets.exceptions.ConnectionClosed:
                logger.warning("WebSocket连接已关闭")
                if self.heartbeat_task:
                    self.heartbeat_task.cancel()
                    try:
                        await self.heartbeat_task
                    except asyncio.CancelledError:
                        pass
                await asyncio.sleep(5)  # 等待5秒后重连
                
            except Exception as e:
                logger.error(f"连接发生错误: {e}")
                if self.heartbeat_task:
                    self.heartbeat_task.cancel()
                    try:
                        await self.heartbeat_task
                    except asyncio.CancelledError:
                        pass
                await asyncio.sleep(5)  # 等待5秒后重连

class XianyuApp:
    def __init__(self):
        self.config = ConfigManager()
        self.login_manager = LoginManager(self.config)
        self.xianyu_live = None
        self.cookie_manager = CookieManager()
        self.cookie_injector = CookieInjector()
        
    async def start(self):
        """启动应用"""
        try:
            # 1. 获取启动选项
            no_previous_login = False
            while True:
                choice = get_startup_option(no_previous_login)
                if choice == '4':
                    logger.info(get_response("system", "shutdown"))
                    return
                    
                if choice == '1' and not self.config.cookies_str:
                    logger.error(get_response("error", "cookie_invalid"))
                    no_previous_login = True
                    continue
                    
                # 2. 处理登录
                cookies_str = await self.login_manager.handle_login(choice)
                if not cookies_str:
                    logger.error(get_response("error", "login_failed"))
                    if choice in ['2', '3']:
                        return
                    no_previous_login = True
                    continue
                    
                # 3. 验证token
                if not await self.login_manager.validate_token(cookies_str):
                    logger.error(get_response("error", "token_invalid"))
                    if choice in ['2', '3']:
                        return
                    no_previous_login = True
                    continue
                    
                # 4. 启动主程序
                try:
                    self.xianyu_live = XianyuLive(cookies_str)
                    await self.xianyu_live.main()
                except Exception as e:
                    logger.error(f"连接发生错误: {e}")
                    if choice in ['2', '3']:
                        return
                    no_previous_login = True
                    continue
                    
        except KeyboardInterrupt:
            handle_exit()
        except Exception as e:
            logger.error(f"程序运行出错: {e}")
            logger.exception("详细错误信息：")
            handle_exit()

def handle_exit(signum=None, frame=None):
    """处理程序退出"""
    print("\n" + get_response("system", "shutdown"))
    # 禁用所有日志输出
    logger.remove()
    # 关闭所有连接
    if hasattr(app, 'xianyu_live') and app.xianyu_live:
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.stop()
            loop.close()
        except Exception:
            pass
    sys.exit(0)

def handle_message(message):
    """处理接收到的消息"""
    try:
        msg_type = message.get('type')
        msg_content = message.get('content', {})
        
        # 记录特殊消息的回复
        special_replies = {
            'image': "稍等，我看一下图片内容...",
            'voice': "你好，这边听不了语音哈，麻烦您发送文字消息。"
        }
        
        if msg_type in special_replies:
            reply = special_replies[msg_type]
            logger.info(f"收到{msg_type}消息")
            # 记录到对话历史
            if hasattr(app, 'xianyu_live'):
                app.xianyu_live.message_history.append({
                    'role': 'assistant',
                    'content': reply
                })
            return reply
            
        # 处理文本消息
        if msg_type == 'text':
            text = msg_content.get('text', '')
            if not text:
                return None
                
            # 生成回复
            reply = app.generate_reply(text)
            return reply
            
    except Exception as e:
        logger.error(f"处理消息时出错: {e}")
        return None

def get_startup_option(no_previous_login=False):
    """获取用户启动选项"""
    print("\n==================================================")
    print("                    闲鱼自动回复助手")
    print("==================================================")
    print(get_response("prompt", "login_options"))
    print("\n==================================================")
    
    while True:
        choice = input("请输入选项" + ("(2-4): " if no_previous_login else "(1-4): ")).strip()
        if no_previous_login and choice == '1':
            print("无效的选项，请重新输入")
            continue
        if choice in ['1', '2', '3', '4']:
            return choice
        print("无效的选项，请重新输入")

def get_cookie_update_method():
    """获取Cookie更新方式"""
    while True:
        print(get_response("prompt", "cookie_update"))
        
        choice = input("请输入选项(1-3): ").strip()
        if choice in ['1', '2', '3']:
            return choice
        print("无效的选项，请重新输入")

def get_manual_cookies():
    """获取手动输入的Cookie"""
    print("\n==================================================")
    print("请从浏览器F12中复制完整的cookie文本")
    print("如果终端弹出窗口，请选择'粘贴为一行'")
    print("粘贴完成后按回车键结束输入")
    print("==================================================")
    
    cookie_text = input().strip()
    if not cookie_text:
        logger.error("未输入Cookie文本")
        return None
    return cookie_text

def parse_cookie_text(cookie_text):
    """解析Cookie文本"""
    try:
        # 清理Cookie文本
        cookie_text = cookie_text.replace('\t', ' ').replace('\n', ' ')
        while '  ' in cookie_text:
            cookie_text = cookie_text.replace('  ', ' ')
        
        # 分割Cookie
        cookies = {}
        parts = cookie_text.split(';')
        for part in parts:
            part = part.strip()
            if not part:
                continue
                
            # 处理键值对
            if '=' in part:
                key, value = part.split('=', 1)
                key = key.strip()
                value = value.strip()
                cookies[key] = value
        
        # 检查必需字段
        required_fields = ['_m_h5_tk', '_m_h5_tk_enc', 'cookie2', 't', 'unb', 'tracknick', '_tb_token_', 'tfstk']
        missing_fields = [field for field in required_fields if field not in cookies]
        
        if missing_fields:
            logger.warning(f"缺少以下必需的cookie: {', '.join(missing_fields)}")
            return None
            
        return cookies
    except Exception as e:
        logger.error(f"Cookie解析失败: {e}")
        return None

def main():
    """主函数"""
    try:
        # 设置信号处理
        signal.signal(signal.SIGINT, handle_exit)
        signal.signal(signal.SIGTERM, handle_exit)
        
        # 初始化应用
        global app
        app = XianyuApp()
        
        # 启动应用
        asyncio.run(app.start())
    except KeyboardInterrupt:
        handle_exit()
    except Exception as e:
        logger.error(f"程序运行出错: {e}")
        handle_exit()

if __name__ == "__main__":
    main()
