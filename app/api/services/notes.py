"""
笔记模块
负责笔记的存储、检索、管理
"""

import json
import os
from datetime import datetime
from typing import List, Dict, Optional


class Notes:
    """笔记类
    1. 初始化笔记存储路径，加载已有笔记
    2. 添加笔记
        2.1 自动生成笔记ID
        2.2 存储笔记内容、标题、标签、创建时间、更新时间
        2.3 保存笔记到文件
    3. 搜索笔记
        3.1 根据ID获取笔记
    4. 更新笔记
     4.1 根据ID更新笔记内容、标题、标签、更新时间
    5. 删除笔记
        5.1 根据ID删除笔记
    6. 列出笔记
        6.1 支持分页查询
    """
    pass

    def __init__(self, storage_path: str = "notes") -> None:
        """
        初始化笔记存储路径，加载已有笔记
        :param storage_path:
        """
        self.storage_path = storage_path
        if not os.path.exists(self.storage_path):
            os.makedirs(self.storage_path)
        self.note_path = os.path.join(self.storage_path, "notes.json")
        if not os.path.exists(self.note_path):
            with open(self.note_path, "w", encoding="utf-8") as f:
                json.dump([], f, ensure_ascii=False)


        self._load_notes()

    def _load_notes(self)->None:
        with open(self.note_path, "r", encoding="utf-8") as f:
            data = f.read()
            if data:
                self.notes = json.loads(data)
            else:
                self.notes = []

    def add_note(self, note: Dict)->int:
        if not self.notes:
            self.notes = []

        note["id"] = len(self.notes)
        note["created_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        note["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.notes.append(note)

        with open(self.note_path, "w", encoding="utf-8") as f:
            json.dump(self.notes, f, ensure_ascii=False, indent=4)
        return note["id"]

    def get_note_by_id(self, note_id: int) -> Optional[Dict]:
        for note in self.notes:
            if note["id"] == note_id:
                return note
        return None

    def edit_note(self, note_id: int, note: Dict)->bool:
        for idx, existing_note in enumerate(self.notes):
            if existing_note["id"] == note_id:
                note["id"] = note_id
                note["created_at"] = existing_note["created_at"]
                note["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self.notes[idx] = note
                with open(self.note_path, "w", encoding="utf-8") as f:
                    json.dump(self.notes,f, ensure_ascii=False, indent=4)
                return True
        return False

    def list_notes(self) -> List[Dict]:
        return self.notes

    def delete_note(self, note_id: int)->bool:
        for idx, existing_note in enumerate(self.notes):
            if existing_note["id"] == note_id:
                del self.notes[idx]
                with open(self.note_path, "w", encoding="utf-8") as f:
                    json.dump(self.notes, f,ensure_ascii=False, indent=4)
                return True
        return False
# *******************************************************************
    def search_notes(self, query: str, top_k: int = 5) -> list[dict]:
        """
        搜索笔记：支持标题、内容和标签匹配
        """
        query = query.strip().lower()
        if not query:
            return []
        all_notes = self.list_notes()
        results = []
        for n in all_notes:
            title = n.get("title", "").lower()
            content = n.get("content", "").lower()
            tags = [t.lower() for t in n.get("tags", [])]
            if query in title or query in content or any(query in t for t in tags):
                results.append(n)
            if len(results) >= top_k:
                break
        return results

note = Notes()
