import os
from openai import OpenAI
from loguru import logger
import requests
import base64
from default_responses import get_response

class ImageProcessor:
    def __init__(self, image_prompt=None):
        # 加载环境变量
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.error("未设置OPENAI_API_KEY环境变量")
            raise ValueError("未设置OPENAI_API_KEY环境变量")
            
        # 初始化API客户端
        self.client = OpenAI(
            api_key=api_key,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            timeout=30.0
        )
        
        # 使用传入的提示词，不再自行加载
        self.image_prompt = image_prompt
        if not self.image_prompt:
            logger.error("未提供图片处理提示词")
            raise ValueError("未提供图片处理提示词")

    def try_direct_url(self, image_url, prompt=None):
        """尝试直接使用URL方式处理图片"""
        try:
            if prompt is None:
                prompt = self.image_prompt
                
            if not prompt:
                logger.error("未设置图片处理提示词")
                return None
                
            # 记录开始处理
            logger.info(get_response("special", "image", sub_key="processing"))
                
            completion = self.client.chat.completions.create(
                model="qwen-vl-plus",
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": image_url,
                                "detail": "high"
                            }
                        }
                    ]
                }],
                max_tokens=500,
                temperature=0.7,
                top_p=0.8,
                timeout=30
            )
            
            image_description = completion.choices[0].message.content
            if not image_description:
                logger.error(get_response("special", "image", sub_key="failed"))
                return None
                
            logger.info(get_response("special", "image", sub_key="success"))
            return image_description
        except Exception as e:
            logger.warning(f"直接URL方式处理失败: {e}")
            return None

    def try_base64_url(self, image_url, prompt=None):
        """尝试使用base64方式处理图片"""
        try:
            if prompt is None:
                prompt = self.image_prompt
                
            if not prompt:
                logger.error("未设置图片处理提示词")
                return None
                
            # 记录开始处理
            logger.info(get_response("special", "image", sub_key="processing"))
                
            # 下载图片并获取Content-Length
            image_content, content_length = self.download_image(image_url)
            if not image_content:
                logger.error("无法下载图片")
                return None
                
            # 将图片编码为base64格式
            base64_image = base64.b64encode(image_content).decode('utf-8')
            
            completion = self.client.chat.completions.create(
                model="qwen-vl-plus",
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{base64_image}",
                                "detail": "high"
                            }
                        }
                    ]
                }],
                max_tokens=500,
                temperature=0.7,
                top_p=0.8,
                timeout=30
            )
            
            image_description = completion.choices[0].message.content
            if not image_description:
                logger.error(get_response("special", "image", sub_key="failed"))
                return None
                
            logger.info(get_response("special", "image", sub_key="success"))
            return image_description
        except Exception as e:
            logger.error(f"base64方式处理失败: {e}")
            return None
            
    def download_image(self, image_url):
        """下载图片并返回内容和大小"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                'Referer': 'https://www.goofish.com/',
                'Connection': 'keep-alive'
            }
            response = requests.get(image_url, headers=headers, timeout=15)
            if response.status_code == 200:
                content = response.content
                content_length = len(content)
                logger.info(f"成功下载图片，大小: {content_length} 字节")
                return content, content_length
            else:
                logger.error(f"下载图片失败，状态码: {response.status_code}")
                return None, 0
        except Exception as e:
            logger.error(f"下载图片异常: {e}")
            return None, 0

    def process_image(self, image_url):
        """处理图片并生成描述"""
        try:
            # 处理imgur链接
            if 'imgur.com' in image_url:
                # 如果是相册链接，转换为直接图片链接
                if '/a/' in image_url:
                    image_id = image_url.split('/a/')[1].split('/')[0]
                    image_url = f"https://i.imgur.com/{image_id}.jpg"
            
            # 首先尝试直接URL方式
            logger.info("尝试直接URL方式处理图片...")
            result = self.try_direct_url(image_url)
            if result:
                return result
                
            # 如果直接URL方式失败，尝试base64方式
            logger.info("直接URL方式失败，尝试base64方式处理图片...")
            result = self.try_base64_url(image_url)
            if result:
                return result
                
            logger.error("所有处理方式均失败")
            return None
            
        except Exception as e:
            logger.error(f"图片处理失败: {e}")
            return None

    def is_special_message(self, message):
        """判断是否为特殊消息（图片、语音等）"""
        try:
            if "1" in message and "10" in message["1"]:
                detail_notice = message["1"]["10"].get("detailNotice", "")
                reminder_content = message["1"]["10"].get("reminderContent", "")
                
                # 检查是否包含方括号格式的特殊消息
                if detail_notice.startswith("[") and detail_notice.endswith("]"):
                    return detail_notice[1:-1]  # 返回方括号中的内容
                elif reminder_content.startswith("[") and reminder_content.endswith("]"):
                    return reminder_content[1:-1]  # 返回方括号中的内容
                
                # 检查是否为语音消息
                if "语音" in detail_notice or "语音" in reminder_content:
                    return "语音"
        except Exception as e:
            logger.error(f"特殊消息判断失败: {e}")
        return None

    def get_message_type(self, message):
        """获取消息类型"""
        special_type = self.is_special_message(message)
        if special_type:
            return special_type
        return "正常消息"  # 修改为更友好的提示 