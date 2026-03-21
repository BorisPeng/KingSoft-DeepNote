"""
笔记相关API路由
"""

"""
1. 添加笔记
    1.1 URL : /note
    1.2 方法: POST
    1.3 请求体:
        {
        "content": "笔记内容",
        "title": "笔记标题",
        "tags": ["标签1", "标签2"](可选)
        }
    1.4 返回:
        {
            "id": "笔记ID"
        }
2. 根据ID获取笔记
    2.1 URL : /notes/<note_id>
    2.2 方法: GET
    2.3 返回:
        {
            "id": "笔记ID",
            "title": "笔记标题",
            "content": "笔记内容",
            "tags": ["标签1", "标签2"],
            "source": "来源",
            "created_at": "创建时间",
            "updated_at": "更新时间"
        }
3. 列出笔记
    3.1 URL : /notes
    3.2 方法: GET
    3.3 查询参数:
        limit: 限制返回数量(可选，默认为50)
        offset: 偏移量(可选，默认为0)
    3.4 返回:
        {
            "result": [
                {
                    "id": "ID",
                    "title": "笔记标题",
                    "content": "笔记内容",
                    "tags": ["标签1", "标签2"],
                    "source": "来源",
                    "created_at": "创建时间",
                    "updated_at": "更新时间"
                }
            ]
        }
4. 删除笔记
    4.1 URL : /note/<note_id>
    4.2 方法: DELETE
    4.3 返回:
        {
            "message": "删除成功"
        }
5. 更新笔记
    5.1 URL : /note/<note_id>
    5.2 方法: PUT
    5.3 请求体:
        {
            "content": "新内容(可选)",
            "title": "新标题(可选)",
            "tags": ["新标签1", "新标签2"](可选),
            "source": "新来源(可选)"
        }
    5.4 返回:
        {
            "message": "更新成功"
        }
6. 搜索笔记
    6.1 URL : /note/search
    6.2 方法: POST
    6.3 请求体:
        {
            "query": "搜索查询",
            "top_k": 5 (可选，默认为5)
        }
    6.4 返回:
        [
            {
                "id": "笔记ID",
                "title": "笔记标题",
                "content": "笔记内容",
                "tags": ["标签1", "标签2"],
                "similarity": 相似度分数
            }
        ]

"""

from flask import Blueprint, request, jsonify
from ..services.notes import note

note_bp = Blueprint('note', __name__, url_prefix='/api')


@note_bp.route('/notes',methods=["GET"])
def get_notes():
    limit = int(request.args.get('limit', 50))
    offset = int(request.args.get('offset', 0))
    notes = note.list_notes()
    return jsonify({
        "result": notes[offset:offset + limit]
    })


@note_bp.route('/note', methods=["POST"])
def add_note():
    """添加笔记"""
    note_data = request.json
    note_id = note.add_note(note_data)
    return jsonify({
        "id": note_id
    })


@note_bp.route('/note/<int:note_id>', methods=["GET"])
def get_note(note_id: int):
    """根据ID获取笔记"""
    note_data = note.get_note_by_id(note_id)
    if not note_data:
        return jsonify({"error": "笔记未找到"}), 404
    return jsonify(note_data)


@note_bp.route(rule='/note/<int:note_id>', methods=["PUT"])
def edit_note(note_id: int):
    """更新笔记"""
    note_data = request.json
    success = note.edit_note(note_id, note_data)
    if not success:
        return jsonify({"error": "笔记未找到"}), 404
    return jsonify({"message": "更新成功"})


@note_bp.route(rule='/note/<int:note_id>', methods=["DELETE"])
def delete_note(note_id: int):
    """删除笔记"""
    success = note.delete_note(note_id)
    if not success:
        return jsonify({"error": "笔记未找到"}), 404
    return jsonify({"message": "删除成功"})

# ***************************************************************************
# 搜索笔记 可同时匹配标题，内容，标签
@note_bp.route('/note/search', methods=["POST"])
def search_note():
    data = request.json
    query = data.get("query", "").strip()
    top_k = data.get("top_k", 5)

    results = note.search_notes(query, top_k)
    return jsonify(results)


