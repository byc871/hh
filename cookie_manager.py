from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time
import json
import os
import re
from loguru import logger
import logging

# 禁用 Selenium 的日志输出
selenium_logger = logging.getLogger('selenium')
selenium_logger.setLevel(logging.ERROR)
selenium_logger.propagate = False

class CookieManager:
    def __init__(self):
        self.cookies = None
        self.driver = None
        self.required_cookies = [
            '_m_h5_tk',
            '_m_h5_tk_enc',
            'cookie2',
            't',
            'unb',
            'tracknick',
            '_tb_token_',
            'sgcookie',
            'tfstk'
        ]
        self.critical_cookies = [
            '_m_h5_tk',
            '_m_h5_tk_enc',
            'cookie2',
            't',
            'unb'
        ]
        
    def setup_driver(self):
        """设置并初始化 ChromeDriver"""
        # 禁用 TensorFlow 提示
        os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
        os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'
        
        chrome_options = Options()
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument("--disable-notifications")
        chrome_options.add_experimental_option("prefs", {
            "profile.default_content_setting_values.notifications": 2
        })
        chrome_options.add_argument('--log-level=3')
        
        try:
            # 使用 webdriver-manager 自动下载和管理 chromedriver
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            logger.info("浏览器启动成功")
        except Exception as e:
            logger.error(f"浏览器启动失败: {e}")
            raise
            
    def clear_cookies(self):
        """清除浏览器中的所有 cookies"""
        if not self.driver:
            logger.error("浏览器未初始化")
            return False
            
        try:
            self.driver.delete_all_cookies()
            logger.info("已清除浏览器中的所有 cookies")
            return True
        except Exception as e:
            logger.error(f"清除 cookies 失败: {e}")
            return False
        
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
            
    def get_cookies(self):
        """获取当前页面的 cookies"""
        if not self.driver:
            logger.error("浏览器未初始化")
            return None
            
        try:
            cookies = self.driver.get_cookies()
            # 将 cookies 转换为字符串格式
            cookie_str = '; '.join([f"{cookie['name']}={cookie['value']}" for cookie in cookies])
            
            # 验证获取的 Cookie 是否包含所有必需字段
            cookie_dict = self.parse_cookie_string(cookie_str)
            missing_cookies = [cookie for cookie in self.required_cookies if cookie not in cookie_dict]
            
            if missing_cookies:
                logger.error(f"获取的 Cookie 缺少必需字段: {', '.join(missing_cookies)}")
                return None
                
            return cookie_str
            
        except Exception as e:
            logger.error(f"获取 cookies 失败: {e}")
            return None

    def get_manual_cookies(self):
        """获取手动输入的cookie"""
        print("\n==================================================")
        print("请从浏览器F12中复制完整的cookie文本")
        print("\n*** 重要提示 ***")
        print("如果终端弹出窗口，请选择'粘贴为一行'")
        print("==================================================")
        
        try:
            # 读取所有输入行
            lines = []
            while True:
                try:
                    line = input().strip()
                    if not line:  # 空行表示输入结束
                        break
                    # 移除PowerShell的行前缀">>"
                    line = line.replace('>>', '').strip()
                    lines.append(line)
                except EOFError:
                    break
            
            # 合并所有行
            cookie_text = ' '.join(lines)
            if not cookie_text:
                logger.error("未输入cookie文本")
                return None
                
            # 解析cookie文本
            cookies = self.parse_cookie_text(cookie_text)
            if not cookies:
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

    def parse_cookie_text(self, cookie_text):
        """
        解析单行粘贴的Cookie文本。
        假设文本是从浏览器F12复制的表格数据，粘贴时换行符变为空格。
        """
        try:
            cookies = {}
            # 移除可能的PowerShell前缀">>"并按空白分割成单词列表
            words = cookie_text.replace('>>', '').strip().split()

            if not words:
                logger.error("输入的Cookie文本在分割后为空")
                return None

            # 遍历词语列表，查找必需的cookie名称
            for i in range(len(words)):
                current_word = words[i]

                # 检查当前词语是否是我们需要的cookie名称之一
                if current_word in self.required_cookies:
                    # 确保后面紧跟着一个词语作为它的值
                    if i + 1 < len(words):
                        cookie_name = current_word
                        cookie_value = words[i+1]
                        cookies[cookie_name] = cookie_value
                    else:
                        # 如果Cookie名称是列表的最后一个词，说明缺少值
                        logger.warning(f"找到必需Cookie名称 '{current_word}' 但其后没有对应的值")

            # 检查是否所有必需字段都已找到
            missing_fields = [field for field in self.required_cookies if field not in cookies]

            if missing_fields:
                logger.warning(f"缺少以下必需的cookie: {', '.join(missing_fields)}")
                return None

            logger.success("Cookie解析成功")
            return cookies

        except Exception as e:
            logger.error(f"Cookie解析失败: {e}")
            return None
    
    def format_cookie_string(self, cookies):
        """将cookie字典格式化为字符串"""
        return '; '.join([f"{k}={v}" for k, v in cookies.items()])
        
    def inject_cookies(self, cookie_str):
        """将 cookies 注入到 .env 文件"""
        try:
            # 读取现有的 .env 文件
            env_path = '.env'
            existing_content = {}
            
            if os.path.exists(env_path):
                try:
                    with open(env_path, 'r', encoding='utf-8') as f:
                        for line in f:
                            line = line.strip()
                            if line and '=' in line and not line.startswith('#'):
                                key, value = line.split('=', 1)
                                existing_content[key.strip()] = value.strip()
                except Exception as read_err:
                    logger.error(f"读取现有 .env 文件时出错: {read_err}")
            
            # 更新或添加 COOKIES_STR
            existing_content['COOKIES_STR'] = cookie_str
            
            # 写入更新后的内容
            with open(env_path, 'w', encoding='utf-8') as f:
                for key, value in existing_content.items():
                    f.write(f'{key}={value}\n')
                    
            logger.success("Cookie已成功注入到.env文件")
            return True
            
        except Exception as e:
            logger.error(f"注入Cookie失败: {e}")
            return False
            
    def close(self):
        """关闭浏览器"""
        if self.driver:
            self.driver.quit()
            self.driver = None

def get_and_inject_cookies():
    """获取并注入 cookies 的主函数"""
    cookie_manager = CookieManager()
    
    try:
        # 设置并启动浏览器
        cookie_manager.setup_driver()
        
        # 访问闲鱼消息页面
        cookie_manager.driver.get('https://www.goofish.com/im')
        logger.info("已打开闲鱼消息页面")
        
        # 清除现有的 cookies
        cookie_manager.clear_cookies()
        
        # 等待用户手动登录
        logger.info("请手动登录闲鱼账号...")
        logger.info("注意：请确保登录成功后再确认")
        
        # 等待用户确认是否已登录
        while True:
            user_input = input("是否已完成登录？(y/n): ").lower()
            if user_input == 'y':
                # 获取 cookies
                cookie_str = cookie_manager.get_cookies()
                if not cookie_str:
                    logger.error("获取 cookies 失败，请重新登录")
                    continue
                    
                # 验证 Cookie 有效性
                if not cookie_manager.verify_cookie_consistency(cookie_str, cookie_str):
                    logger.error("Cookie 验证失败，请重新登录")
                    continue
                    
                # 注入 cookies
                if cookie_manager.inject_cookies(cookie_str):
                    logger.success("Cookie 注入完成")
                    return cookie_str
                else:
                    logger.error("Cookie 注入失败")
                    return None
                    
            elif user_input == 'n':
                logger.info("用户选择取消操作，正在关闭程序...")
                cookie_manager.close()
                return None
            else:
                logger.warning("输入无效，请输入 'y' 或 'n'")
                
    except Exception as e:
        logger.error(f"发生错误: {e}")
        return None
    finally:
        cookie_manager.close()

if __name__ == "__main__":
    get_and_inject_cookies() 