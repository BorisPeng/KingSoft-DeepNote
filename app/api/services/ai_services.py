# backend/api/services/ai_service.py
"""
AI服务核心类
"""

import json

import requests
from typing import Dict, List, Any, Optional, Generator
from abc import ABC, abstractmethod
from enum import Enum

from flask_app.app.config.settings import settings

# 导入笔记模块
from flask_app.app.api.services.notes import note



role = {
    'bot': 'assistant',
    'user': 'user'
}


class AIProvider(Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    COHERE = "cohere"
    CLAUDE = "claude"
    QWEN = "qwen"
    DEEPSEEK = "deepseek"
    BIGMODEL = "bigmodel"


class AIPluginInterface(ABC):
    """AI插件接口"""

    @abstractmethod
    def get_name(self) -> str:
        """获取插件名称"""
        pass

    @abstractmethod
    def get_description(self) -> str:
        """获取插件描述"""
        pass

    @abstractmethod
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """验证配置"""
        pass

    @abstractmethod
    def generate_response(self, messages: List[Dict], new_message: str, **kwargs) -> Dict[str, Any]:
        """生成响应"""
        pass

NOTE_SEARCH_KEYWORDS = ["搜索笔记", "查笔记", "知识库", "find notes", "search notes", "rag"]
class OpenAIPlugin(AIPluginInterface):
    """OpenAI插件实现"""

    def __init__(self, base_url: str, api_key: str, model: str):
        self.base_url = base_url
        self.api_key = api_key
        self.model = model

    def get_name(self) -> str:
        return "OpenAI"

    def get_description(self) -> str:
        return "OpenAI API服务"

    def validate_config(self, config: Dict[str, Any]) -> bool:
        return all([config.get('base_url'), config.get('api_key'), config.get('model')])

    def generate_response(self, messages, new_message: str, **kwargs)-> Generator[str, Any, Dict[str, Any]]:
        """

        1. 初始化客户端和参数
           - 创建OpenAI客户端实例，配置base_url和api_key
           - 从kwargs提取use_knowledge（是否启用知识库）、persona（角色设定）
           - 初始化knowledge_context为空字符串，用于存储知识上下文

        2. 处理角色设定
           - 如果persona不为空，在messages开头添加系统角色消息

        3. 检测用户是否要求搜索笔记
           - 遍历预设关键词（包含中英文）检查new_message
           - 如果检测到搜索意图，标记explicit_note_search为True
           - 提取纯查询内容（去除搜索指令）
           - 更新new_message为提取后的内容

        4. 检查是否启用笔记搜索
           - search_notes = kwargs中的search_notes或explicit_note_search
           - 如果search_notes为True且new_message不为空
             - 调用note.search_notes(query=new_message, top_k=5)搜索相关笔记
             - 将搜索结果格式化为字符串，添加到knowledge_context

        5. 检查是否启用知识库搜索（use_knowledge）
           - 如果use_knowledge为True且new_message不为空
             - 调用knowledge_base.search_knowledge(new_message, top_k=3)搜索相关知识
             - 将搜索结果格式化为字符串，追加到knowledge_context

        6. 整合知识上下文到消息中
           - 如果knowledge_context不为空
             - 复制messages避免修改原数据
             - 追加系统消息，指示AI结合知识上下文回答

        7. 调用OpenAI API
           - 获取模型参数：temperature(默认0.7)、max_tokens(默认2048)
           - 将new_message作为用户消息追加到messages
           - 调用client.chat.completions.create创建聊天完成
           - 设置stream为True启用流式响应，传入temperature和max_tokens

        8. 处理流式响应
           - 遍历response中的每个chunk
           - 提取answer_chunk = chunk.choices[0].delta.content
           - 如果answer_chunk不为空：
             - 将answer_chunk包装为JSON：json.dumps({'text': answer_chunk, 'reason': False})
             - 使用yield返回SSE格式数据：f"data: {json_str}\n"

        9. 返回响应
           - 通过yield逐个返回响应块
           - 每个chunk包含部分回答内容，前端可实时显示
        """
        # 从 kwargs 中获取最终配置
        base_url = kwargs.get('base_url')
        api_key = kwargs.get('api_key')
        model = kwargs.get('model')
        is_stream = kwargs.get('stream', True)
        search_notes_enabled = kwargs.get('search_notes', True)

        knowledge_context = ""
        explicit_note_search = False
        query = new_message.strip()


        # 3. 检测是否要求搜索笔记
        q_lower = query.lower()
        for keyword in NOTE_SEARCH_KEYWORDS:
            if keyword in q_lower:
                explicit_note_search = True
                q_lower = q_lower.replace(keyword, "")
                query = q_lower.strip()
                break

        if not query:
            # 如果去除搜索指令后查询内容为空，则直接返回提示
            yield self._format_sse({"text": "请输入您想要查询的具体内容。", "reason": False})
            return {"status": "user_query_empty"}

            # 4. 检查是否启用笔记搜索
        if search_notes_enabled or explicit_note_search:
            # 调用笔记搜索服务
            note_results = note.search_notes(query=query, top_k=5)

            if note_results:
                # 格式化搜索结果
                formatted_notes = []
                for idx, n in enumerate(note_results):
                    # 使用 title 和 content 来构造上下文
                    formatted_notes.append(
                        f"## 笔记 {idx + 1}: {n.get('title', '无标题')}\n内容: {n.get('content', '无内容')}"
                    )

                knowledge_context = "\n---\n".join(formatted_notes)

        # 6. 整合知识上下文到消息中
        final_messages = messages[:]  # 复制消息列表

        if knowledge_context:
            system_prompt = (
                "你是一个知识增强型AI助手，请你仔细阅读以下从用户笔记中检索到的相关知识，"
                "并严格结合这些知识来回答用户的问题。如果知识中不包含相关信息，请明确告知。"
                f"\n\n--- 检索到的知识 ---\n{knowledge_context}\n----------------------"
            )
            final_messages.insert(0, {"role": "system", "content": system_prompt})

        # 7. 构建最终 API 请求体
        final_messages.append({"role": "user", "content": query})
        if not api_key:
            return {"error": "Missing API key"}
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        # 智谱AI的 URL 已在 settings 中包含 /api/paas/v4，所以只需要 /chat/completions
        url_path = "/chat/completions"
        base_url = base_url.rstrip("/")

        if "bigmodel" in base_url:
            full_url = f"{base_url}/chat/completions"
        else:
            if base_url.endswith("/v1"):
                full_url = f"{base_url}/chat/completions"
            else:
                full_url = f"{base_url}/v1/chat/completions"

        payload = {
            "model": model,
            "messages": final_messages,
            "stream": is_stream,
            "temperature": 0.7,  # 可调参数
            "max_tokens": 2048  # 可调参数
        }



        # 8. 发起请求并处理流式响应
        try:
            print("=== FINAL PAYLOAD SENT TO DEEPSEEK ===")
            print(json.dumps(payload, indent=2, ensure_ascii=False))
            # 使用 requests.post 发送请求，设置 stream=True 接收流式数据
            response = requests.post(
                full_url,
                headers=headers,
                json=payload,
                stream=True,
                timeout=300  # 设置超时时间
            )
            response.raise_for_status()  # 检查 HTTP 错误

            # 遍历响应流
            for line in response.iter_lines():# iter_lines() 是 requests 提供的方法，它会一行一行地读取网络流
                if line:
                    line = line.decode('utf-8')# 把二进制数据解码成字符
                    if line.startswith('data: '):# SSE 协议规定数据以 "data: " 开头
                        data_str = line[6:].strip()# 去掉 "data: " 前缀
                        if data_str == '[DONE]':# AI 发送 "[DONE]" 表示它说完了
                            break

                        try:
                            # 解析 chunk
                            chunk = json.loads(data_str)# 把 JSON 字符串变回 Python 字典
                            # 提取内容
                            content = chunk.get('choices', [{}])[0].get('delta', {}).get('content')

                            if content:
                                # 9. 使用 yield 返回 SSE 格式数据
                                yield self._format_sse({"text": content, "reason": False})

                        except json.JSONDecodeError:
                            # 忽略无法解析的行
                            continue

        except requests.exceptions.RequestException as e:
            # 处理网络请求错误
            error_message = f"API 请求失败: {type(e).__name__} - {e}"
            yield self._format_sse({"text": error_message, "reason": True})
            return {"error": str(e)}
        # 正常完成时的返回语句
        return {"status": "finished"}
    def _format_sse(self, data: Dict[str, Any]) -> str:
        """将字典格式化为 SSE 格式的字符串"""
        json_str = json.dumps(data, ensure_ascii=False)
        return f"data: {json_str}\n\n"


class DeepSeekPlugin(OpenAIPlugin):
    """DeepSeek插件实现
    1. 继承自OpenAIPlugin，复用其方法
    2. 重写get_name和get_description方法
    3. 重写validate_config方法
    4. 其他方法保持不变
    """

    def get_name(self):
        return "DeepSeek"

    def get_description(self):
        return "DeepSeek API服务"

    def validate_config(self, config: Dict[str, Any]) -> bool:
        return all([config.get('api_key'), config.get('model')])

class BigModelPlugin(OpenAIPlugin):
    """BigModel 智谱AI
    1. 继承自OpenAIPlugin，复用其方法
    2. 重写get_name和get_description方法
    3. 重写validate_config方法
    4. 其他方法保持不变
    """

    def get_name(self):
        return "BigModel"

    def get_description(self):
        return "智谱AI API服务"

    def validate_config(self, config: Dict[str, Any]) -> bool:
        return all([config.get('api_key'), config.get('model')])

class QwenPlugin(OpenAIPlugin):
    """通义千问插件实现
    1. 继承自OpenAIPlugin，复用其方法
    2. 重写get_name和get_description方法
    3. 重写validate_config方法
    4. 其他方法保持不变
    """

    def get_name(self):
        return "Qwen"

    def get_description(self):
        return "通义千问 API服务"

    def validate_config(self, config: Dict[str, Any]) -> bool:
        return all([config.get('api_key'), config.get('model')])

class AIService:
    """AI服务管理类
    1. 初始化并注册所有支持的AI插件(选其一)
        1.1 支持OpenAI插件
        1.2 支持DeepSeek插件
        1.3 支持智谱AI插件
        1.4 支持通义千问插件
    2. 提供获取插件实例的方法
        2.1 根据提供商获取插件实例
        2.2 根据提供商列出模型
    3. 提供列出所有可用AI提供商和模型的方法
        3.1 列出所有可用的AI提供商
        3.2 列出所有可用的模型
    4. 提供生成AI响应的方法
        4.1 处理消息和配置
        4.2 获取对应的插件
        4.3 生成响应（支持流式返回）
    5. 处理配置优先级：前端配置 > 后端默认配置
        5.1 支持前端传递的base_url、api_key、model等配置
        5.2 支持后端默认配置
    6. 支持笔记的集成以增强回答质量
        6.1 支持启用笔记搜索
        6.2 支持结合笔记内容回答用户问题
        6.3 支持前端控制是否搜索笔记
    """

    def __init__(self):
        self.plugins: Dict[str, AIPluginInterface] = {}
        self._register_plugins()

    def _register_plugins(self):
        """注册所有支持的AI插件"""
        # 注册OpenAI插件
        openai_config = settings.AI_PROVIDERS.get('openai', {})
        if openai_config.get('api_key'):  # 只有在配置了API密钥时才注册
            self.plugins["openai"] = OpenAIPlugin(
                base_url=openai_config.get('base_url', 'https://api.openai.com/v1'),
                api_key=openai_config.get('api_key',''),
                model=openai_config.get('model', 'gpt-3.5-turbo')
            )

        # 注册DeepSeek插件
        deepseek_config = settings.AI_PROVIDERS.get('deepseek', {})
        if deepseek_config.get('api_key'):  # 只有在配置了API密钥时才注册
            self.plugins["deepseek"] = DeepSeekPlugin(
                base_url=deepseek_config.get('base_url', "https://api.deepseek.com"),
                api_key=deepseek_config.get('api_key',''),
                model=deepseek_config.get('model', "deepseek-chat")
            )

        # 注册智谱AI插件
        bigmodel_config = settings.AI_PROVIDERS.get('bigmodel', {})
        if bigmodel_config.get('api_key'):  # 只有在配置了API密钥时才注册
            self.plugins["bigmodel"] = BigModelPlugin(
                base_url=bigmodel_config.get('base_url', "https://open.bigmodel.cn/api/paas/v4"),
                api_key=bigmodel_config.get('api_key',''),
                model=bigmodel_config.get('model', "glm-4-flash")
            )

        # 注册Qwen插件
        qwen_config = settings.AI_PROVIDERS.get('qwen', {})
        if qwen_config.get('api_key'):  # 只有在配置了API密钥时才注册
            self.plugins["qwen"] = QwenPlugin(
                base_url=qwen_config.get('base_url', "https://dashscope.aliyuncs.com"),
                api_key=qwen_config.get('api_key',''),
                model=qwen_config.get('model', "qwen-turbo")
            )

    def get_plugin(self, provider: str) -> Optional[AIPluginInterface]:
        """根据提供商获取插件实例"""
        return self.plugins.get(provider)

    def list_providers(self) -> List[Dict[str, str]]:
        """列出所有可用的AI提供商
        1. 遍历已注册的插件
        2. 获取每个插件的名称和描述
        3. 返回提供商列表
        Returns:
            提供商列表
            [
                {
                    'id': 'provider_id',
                    'name': 'Provider Name',
                    'description': 'Provider Description'
                }
            ]

        """
        providers = []
        # TODO 补充逻辑
        for provider_id, plugin_instance in self.plugins.items():
            providers.append({
                'id': provider_id,
                'name': plugin_instance.get_name(),
                'description': plugin_instance.get_description()
            })
        return providers

    def list_models_by_provider(self, provider: str) -> List[Dict[str, str]]:
        """
        根据提供商列出模型
        1. 检查提供商是否在配置中定义了模型列表
        2. 如果定义了，返回配置的模型列表
        3. 否则返回插件的默认模型
        4. 如果提供商不存在，返回空列表

        Args:
            provider: 提供商ID

        Returns:
            模型列表
            [
                {
                    'id': 'model_id',
                    'name': 'Model Name'
                }
            ]
        """
        # TODO 补充逻辑
        # 从 settings 中直接获取该提供商的模型列表
        models = settings.PROVIDER_MODELS.get(provider.lower(), [])
        return models

    def generate_response(self, data: Dict[str, Any], stream: bool = True) -> Any:
        """
        生成AI响应

        1. 处理消息和配置
            1.1 获取提供商和配置
            1.2 获取前端传递的配置，如果未传递则使用后端默认配置
            1.3 获取模型参数
            1.4 获取角色设定
            1.5 构建消息列表
        2. 获取对应的插件
            2.1 根据提供商获取插件实例
            2.2 验证配置
            2.3 设置插件配置
        3. 生成响应（支持流式返回）
            3.1 如果启用流式返回，设置stream参数
            3.2 调用插件的generate_response方法生成响应
        4. 处理配置优先级：前端配置 > 后端默认配置
            4.1 支持前端传递的base_url、api_key、model等配置
            4.2 支持后端默认配置

        5. 支持笔记的集成以增强回答质量
            5.1 支持启用笔记搜索
            5.2 支持结合笔记内容回答用户问题
            5.3 支持前端控制是否搜索笔记
        6. 返回响应结果

        Args:
            data: 包含消息、配置等信息的字典
            stream: 是否启用流式返回

        Returns:
            响应结果
        """
        # 1. 解析请求数据
        provider = data.get("provider", settings.DEFAULT_PROVIDER).lower()
        new_message = data.get("newMessage", "")
        raw_msgs = data.get("messages", [])
        messages = []

        for m in raw_msgs:
            role = m.get("role") or ("user" if m.get("sender") == "user" else "assistant")
            content = m.get("content") or m.get("text")
            if role and content:
                messages.append({"role": role, "content": content})


        # 从请求体中获取可能的覆盖配置
        custom_base_url = data.get("base_url")
        custom_api_key = data.get("api_key")
        custom_model = data.get("model")

        # 2. 获取对应的插件
        plugin = self.get_plugin(provider)
        if not plugin:
            raise ValueError(f"AI提供商 '{provider}' 未注册或配置。")

        # 3. 获取配置
        # 获取后端默认配置
        default_config = settings.AI_PROVIDERS.get(provider, {})

        # 确定最终配置
        final_base_url = custom_base_url or default_config.get('base_url')
        final_api_key = custom_api_key or default_config.get('api_key')
        final_model = custom_model or default_config.get('model')

        # 4. 验证配置
        if not final_api_key or not final_model or not final_base_url:
            raise ValueError(f"提供商 {plugin.get_name()} 的 API 配置不完整。")

        # 5. 生成响应
        # 构造 kwargs 传递给插件的 generate_response
        kwargs = {
            'base_url': final_base_url,
            'api_key': final_api_key,
            'model': final_model,
            'stream': stream,
            'search_notes': data.get('search_notes', True)
        }

        # 调用插件的生成方法
        return plugin.generate_response(
            messages=messages,
            new_message=new_message,
            **kwargs
        )
