# 🚀 XianyuAutoAgent-Enhanced | 闲鱼智能自动回复系统增强提案

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue)](https://www.python.org/)
[![OpenAI](https://img.shields.io/badge/OpenAI-API-green)](https://platform.openai.com/)
[![通义千问](https://img.shields.io/badge/Tongyi-VL--Plus-orange)](https://tongyi.aliyun.com/)

> 本版本为原项目 [**XianyuAutoAgent**](https://github.com/shaxiu/XianyuAutoAgent) 的增强提案，旨在优化使用体验、拓展功能，补充如图片识别、登录方式优化等模块功能。本增强版作为 PR 提交，感谢原项目作者的支持与许可。

---

## 👑 致谢与核心贡献者

### 🧠 原项目作者：[@Shaxiu](https://github.com/shaxiu)
- **职位**：AI 产品经理实习  
- **贡献**：整体架构设计、Agent 流程搭建、原版核心逻辑实现  
- **联系方式**：coderxiu@qq.com / 微信：coderxiu

### 🔬 核心技术支持：[@CVcat](https://github.com/cv-cat)
- **职位**：研发工程师实习（Python、Java、逆向）  
- **贡献**：闲鱼 API 逆向、WebSocket 通信、sign 参数解密  
- **联系方式**：992822653@qq.com / 微信：CVZC15751076989

---

## 💡 本增强版简介

增强版主要对以下功能进行扩展和优化：

### ✅ 登录流程优化
- 支持记忆登录、扫码登录（需 `chromedriver`）、Cookie 登录
- 登录失败时自动 fallback 到其他登录方式

### 🧠 智能消息响应
- 对图片消息自动回复提示
- 对语音消息提醒转文字
- 可自定义默认响应模板（详见 `default_responses.py`）

### 🖼️ 图片解析能力
- 接入 **通义千问 VL-Plus 模型**
- 支持图片内容识别并自动注入 AI Agent 处理流程

### 🔔 特殊消息提示
- 终端提示非文本消息类型（图片/语音）
- 开发时更便于调试与识别

---
## 🔭 未来更新方向

### 1. 飞书集成
- 实现登录失败提醒、消息推送  
- 自动将订单信息同步到飞书多维表格  
- 作为程序中台与个人通知工具使用  

### 2. 数据库业务增强
- 当前 SQLite 数据库仅用于存储会话  
- 计划将其深度接入业务流程：
  - 用户画像构建  
  - 对话历史检索  
  - 订单记录管理等功能  

### 3. 接入 LangChain 实现智能 Agent 编排
- 强化上下文记忆与推理能力  
- 实现基于 SQLite 的自动查询与智能检索  
- 支持结构化任务分发与多 Agent 协作调用

---

## 📦 快速开始

### 环境依赖
- Python 3.8+
- Chrome 浏览器 + 匹配版本 `chromedriver`

### 安装与运行

```bash
# 克隆项目
git clone https://github.com/yourusername/XianyuAutoAgent-Enhanced.git
cd XianyuAutoAgent-Enhanced

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
echo "OPENAI_API_KEY=your_api_key_here" > .env

# 启动程序
python main.py

🧩 模块结构概览
XianyuAutoAgent-Enhanced/
├── main.py              # 主程序入口
├── image_processor.py   # 图片识别模块（调用通义）
├── XianyuAgent.py       # 智能对话管理模块
├── context_manager.py   # 上下文数据库存储
├── cookie_manager.py    # 登录管理
├── prompts/             # 提示词模板
└── utils/               # 工具函数

📜 License
本增强版本遵循原项目的 MIT License。

👋 关于我（增强版贡献者）
你好，我是 BYC，一名正在学习大语言模型和 Agent 技术的在校学生。正在基于个人需求，对本项目进行学习与实践，本次 PR 希望能为项目带来一些实用功能。

📫 联系方式：1677693239@qq.com

如果你喜欢这个程序，请为原项目 XianyuAutoAgent 点一个 ⭐！