# DeepNote: 基于 RAG 与多模型 AI 增强的智能笔记管理系统

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![Flask](https://img.shields.io/badge/Framework-Flask-lightgrey.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)

## 📝 项目简介
**DeepNote** 是一款具备个人知识管理（PKM）能力和 AI 增强功能的智能笔记管理系统。本项目基于 **Flask** 框架开发，提供了一套完整的笔记数据管理 API，并利用现代大模型技术，赋予笔记系统“个人知识问答”能力。系统不仅支持基础的笔记 CRUD 操作，更集成了 **RAG（检索增强生成）** 机制，使用户能够基于个人笔记内容作为上下文，获得定制化的 AI 助手服务。

## ✨ 核心功能
* **智能笔记管理 (CRUD)**：通过独立的 `note_bp` 蓝图提供 RESTful API，支持笔记的增删改查。
* **数据持久化**：采用 `JSON` 文件（`notes.json`）存储，确保了数据的一致性、迁移便利性与可读性。
* **RAG 知识增强**：当用户提问时，系统通过 `search_notes` 检索相关笔记，并将其作为 `system` 提示词注入 AI 上下文，实现基于个人知识的精准问答。
* **多模型插件化架构**：兼容 DeepSeek、智谱 AI (BigModel) 等多个大模型提供商，支持动态 URL 适配与 API 调用。
* **流式传输 (SSE)**：利用 Server-Sent Events 协议实现 AI 回复的实时逐字输出，提升交互体验。
* **一键保存对话**：支持过滤 AI 对话记录，自动优化内容格式并一键保存为新笔记，实现知识闭环。

## 🚀 快速开始

### 1. 环境准备
确保您的电脑已安装 Python 3.8 或更高版本。

### 2. 克隆项目与安装依赖
```bash
# 进入项目目录
pip install flask flask-cors requests

### 3. 项目结构说明

```text
WHUPythonProject/
├── flask_app/
│   ├── main.py              # 程序入口，负责 CORS 配置与蓝图注册
│   ├── api/
│   │   ├── routes.py        # 主路由模块，包含页面渲染与 AI 接口
│   │   └── routes/
│   │       └── notes.py     # 笔记管理 API (CRUD 逻辑)
│   ├── services/
│   │   └── ai_services.py   # AI 核心插件 (包含 AIPluginInterface 类)
│   ├── static/              # 静态资源 (scripts.js, styles.css)
│   └── templates/           # HTML 模板 (home.html, aichat.html)
└── notes.json               # 笔记持久化存储文件

### 4. 运行应用
在终端执行启动命令：
python main.py
* 默认服务将运行在 http://localhost:8009
* 打开浏览器访问首页，进入 AI 聊天室
* 点击界面上的“设置”图标，输入您的 API Key 并选择对应的 Provider (如 DeepSeek 或 BigModel)

### 5. 使用RAG功能
* 在聊天界面勾选“搜索笔记”选项
* 发送消息时，系统会自动从您的 notes.json 中检索相关内容提供给 AI 作为背景知识

## 💡 技术难点与创新
* 兼容性处理：通过基类 OpenAIPlugin 统一了不同厂商 API 的调用逻辑，支持动态适配 V1 或 V4 路径。
* 单例模式：Notes 模块实例化为单例对象，确保系统运行时各模块访问的是同一份笔记数据。
* 检索优化：在笔记的标题、内容和标签中执行字符串匹配，并返回相似度最高的 top_k 结果。

## 🔮 未来展望
* 语义检索：引入向量嵌入技术（Embeddings），将关键词匹配升级为更精确的语义搜索。
* 多模态功能：集成图像识别技术，实现拍照识别并自动生成笔记。
