"""
AI相关API路由
"""

from flask import Blueprint, request, jsonify, render_template, Response
from ..services.ai_services import AIService
from flask_app.app.utils.error_handler import handle_error
from flask_app.app.api.routes.notes import note_bp

ai_service = AIService()

role = {
    'bot': 'assistant',
    'user': 'user'
}

ai_bp = Blueprint('ai', __name__)

"""
1. 流式生成AI响应
    1.1 URL : /stream_generate
    1.2 方法: POST
    1.3 请求体:
        {
            "messages": [
                {
                    "sender": "user",
                    "text": "用户消息内容"
                }
            ],
            "base_url": "https://api.openai.com"(可选),
            "api_key": "your-api-key"(可选),
            "model": "gpt-3.5-turbo"(可选),
            "provider": "openai"(可选),
            "newMessage": "新的用户消息"
        }
    1.4 返回:
        事件流格式的数据(SSE - Server-Sent Events)
        data: {"id": "chatcmpl-123", "object": "chat.completion.chunk", "content": "流式响应内容"}
2. 列出可用的AI提供商
    2.1 URL : /list_providers
    2.2 方法: GET
    2.3 返回:
        [
            {
                "id": "提供商ID",
                "name": "提供商名称"
            }
        ]
3. 根据提供商列出可用的AI模型
    3.1 URL : /list_models
    3.2 方法: GET
    3.3 参数:
        provider: 提供商ID
    3.4 返回:
        [
            {
                "id": "模型ID",
                "name": "模型名称"
            }
        ]            
"""

# 注册笔记路由
ai_bp.register_blueprint(note_bp, url_prefix='/api')


@ai_bp.route('/')
def index():
    return render_template('aichat.html')


@ai_bp.route('/stream_generate', methods=['POST'])
def stream_generate():
    """
    流式生成AI响应的API接口

    请求体:
        {
            "messages": [
                {
                    "sender": "user",
                    "text": "用户消息内容"
                }
            ],
            "base_url": "https://api.openai.com"(可选),
            "api_key": "your-api-key"(可选),
            "model": "gpt-3.5-turbo"(可选),
            "provider": "openai"(可选),
            "newMessage": "新的用户消息"
        }

    返回:
        事件流格式的数据(SSE - Server-Sent Events)
        data: {"id": "chatcmpl-123", "object": "chat.completion.chunk", "content": "流式响应内容"}
    """
    data = request.json
    if not data:
        return jsonify({"error": "请求体不能为空"}), 400

    try:
        response_generator = ai_service.generate_response(data=data, stream=True)

        # 将生成器封装为 Flask 的流式响应
        response = Response(
            response_generator,
            mimetype='text/event-stream'
        )
        # 禁用缓存
        response.headers['Cache-Control'] = 'no-cache'
        response.headers['X-Accel-Buffering'] = 'no'
        return response

    except Exception as e:
        # 确保 handle_error 能正确返回 Flask 响应对象
        return handle_error(e)


@ai_bp.route('/list_providers', methods=['GET'])
def list_providers():
    """
    列出可用的AI提供商

    返回:
        [
            {
                "id": "提供商ID",
                "name": "提供商名称"
            }
        ]
    """
    try:
        providers = ai_service.list_providers()
        return jsonify(providers)
    except Exception as e:
        return handle_error(e)


@ai_bp.route('/list_models', methods=['GET'])
def list_models():
    """
    根据提供商列出可用的AI模型

    参数:
        provider: 提供商ID

    返回:
        [
            {
                "id": "模型ID",
                "name": "模型名称"
            }
        ]
    """
    # 从查询参数中获取 provider ID
    provider_id = request.args.get('provider')

    if not provider_id:
        return jsonify({"error": "缺少 'provider' 参数"}), 400

    try:
        # 调用 AIService 方法获取模型列表
        models = ai_service.list_models_by_provider(provider_id)
        return jsonify(models)
    except Exception as e:
        return handle_error(e)