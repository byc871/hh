import os
import re
from loguru import logger
from dotenv import load_dotenv

class CookieInjector:
    def __init__(self):
        self.required_cookies = [
            '_m_h5_tk',
            '_m_h5_tk_enc',
            'cookie2',
            't',
            'unb',
            'tracknick'
        ]
        self.critical_cookies = [
            '_m_h5_tk',
            '_m_h5_tk_enc',
            'cookie2'
        ]
        
    def parse_cookie_text(self, cookie_text):
        """解析cookie文本，提取关键cookie"""
        cookies = {}
        lines = cookie_text.strip().split('\n')
        
        for line in lines:
            if not line.strip():
                continue
                
            # 使用正则表达式匹配cookie行
            match = re.match(r'([^\t]+)\t([^\t]+)\t([^\t]+)\t([^\t]+)', line)
            if match:
                name, value, domain, path = match.groups()
                if name in self.required_cookies:
                    cookies[name] = value
        
        return cookies
    
    def parse_cookie_string(self, cookie_str: str) -> dict:
        """解析 Cookie 字符串为字典"""
        cookies = {}
        if not cookie_str:
            return cookies
            
        try:
            # 处理分号分隔的 Cookie 字符串
            cookie_pairs = cookie_str.split(';')
            for pair in cookie_pairs:
                pair = pair.strip()
                if '=' in pair:
                    name, value = pair.split('=', 1)
                    cookies[name.strip()] = value.strip()
            return cookies
        except Exception as e:
            logger.error(f"解析 Cookie 字符串失败: {e}")
            return {}
    
    def format_cookie_string(self, cookies):
        """将cookie字典格式化为字符串"""
        return '; '.join([f"{k}={v}" for k, v in cookies.items()])
    
    def verify_cookie_consistency(self, browser_cookie: str, injected_cookie: str) -> bool:
        """验证 Cookie 一致性"""
        try:
            # 解析两种 Cookie 字符串
            browser_cookies = self.parse_cookie_string(browser_cookie)
            injected_cookies = self.parse_cookie_string(injected_cookie)
            
            # 检查关键字段
            for field in self.critical_cookies:
                if field not in browser_cookies or field not in injected_cookies:
                    logger.error(f"Cookie 缺少关键字段: {field}")
                    return False
                    
                if browser_cookies[field] != injected_cookies[field]:
                    logger.error(f"Cookie 字段值不匹配: {field}")
                    return False
                    
            logger.info("Cookie 一致性验证通过")
            return True
            
        except Exception as e:
            logger.error(f"Cookie 一致性验证失败: {e}")
            return False
    
    def inject_cookies(self, cookie_text):
        """注入cookie到.env文件"""
        try:
            # 解析cookie文本
            cookies = self.parse_cookie_text(cookie_text)
            
            # 检查是否包含所有必需的cookie
            missing_cookies = [cookie for cookie in self.required_cookies if cookie not in cookies]
            if missing_cookies:
                logger.warning(f"缺少以下必需的cookie: {', '.join(missing_cookies)}")
                return False
            
            # 格式化cookie字符串
            cookie_string = self.format_cookie_string(cookies)
            
            # 验证 Cookie 格式
            if not self.verify_cookie_consistency(cookie_string, cookie_string):
                logger.error("Cookie 格式验证失败")
                return False
            
            # 读取现有的.env文件
            env_path = '.env'
            env_content = {}
            if os.path.exists(env_path):
                with open(env_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        if '=' in line:
                            key, value = line.strip().split('=', 1)
                            env_content[key] = value
            
            # 更新COOKIES_STR
            env_content['COOKIES_STR'] = cookie_string
            
            # 写入.env文件
            with open(env_path, 'w', encoding='utf-8') as f:
                for key, value in env_content.items():
                    f.write(f"{key}={value}\n")
            
            logger.info("Cookie已成功注入到.env文件")
            return True
            
        except Exception as e:
            logger.error(f"注入cookie时出错: {e}")
            return False
    
    def get_manual_cookies(self):
        """从用户获取cookie文本"""
        print("\n请粘贴cookie文本（从浏览器F12中复制的完整cookie文本）")
        print("粘贴完成后按Ctrl+Z（Windows）或Ctrl+D（Linux/Mac）然后按回车键结束输入")
        print("----------------------------------------")
        
        try:
            lines = []
            while True:
                try:
                    line = input()
                    lines.append(line)
                except EOFError:
                    break
            cookie_text = '\n'.join(lines)
            
            if not cookie_text:
                logger.error("未输入cookie文本")
                return None
                
            # 解析cookie文本
            cookies = self.parse_cookie_text(cookie_text)
            
            # 检查是否包含所有必需的cookie
            missing_cookies = [cookie for cookie in self.required_cookies if cookie not in cookies]
            if missing_cookies:
                logger.warning(f"缺少以下必需的cookie: {', '.join(missing_cookies)}")
                return None
                
            # 格式化cookie字符串
            cookie_str = self.format_cookie_string(cookies)
            
            # 验证 Cookie 格式
            if not self.verify_cookie_consistency(cookie_str, cookie_str):
                logger.error("Cookie 格式验证失败")
                return None
                
            return cookie_str
            
        except Exception as e:
            logger.error(f"获取cookie文本时出错: {e}")
            return None 