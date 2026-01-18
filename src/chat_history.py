import json
import os
import aiofiles
from typing import List, Dict, Optional


class ChatHistoryManager:
    def __init__(self, file_path: Optional[str] = None):
        base_dir = os.path.dirname(os.path.dirname(__file__))
        self.histories_dir = os.path.join(base_dir, "data", "chat_histories")
        os.makedirs(self.histories_dir, exist_ok=True)

        if file_path is None:
            file_path = os.path.join(self.histories_dir, "chat_histories.json")
        self.file_path = file_path

    async def _load_histories(self) -> Dict[str, List[Dict]]:
        if not os.path.exists(self.file_path):
            return {}
        try:
            async with aiofiles.open(self.file_path, "r", encoding="utf-8") as f:
                content = await f.read()
                return json.loads(content)
        except (json.JSONDecodeError, IOError):
            return {}

    async def _save_histories(self, histories: Dict[str, List[Dict]]):
        async with aiofiles.open(self.file_path, "w", encoding="utf-8") as f:
            await f.write(json.dumps(histories, ensure_ascii=False, indent=2))

    async def get_history(self, document_id: str) -> List[Dict]:
        histories = await self._load_histories()
        return histories.get(document_id, [])

    async def save_history(self, document_id: str, history: List[Dict]):
        histories = await self._load_histories()
        histories[document_id] = history
        await self._save_histories(histories)

    async def add_message(self, document_id: str, role: str, content: str):
        histories = await self._load_histories()
        if document_id not in histories:
            histories[document_id] = []
        histories[document_id].append({"role": role, "content": content})
        await self._save_histories(histories)

    async def clear_history(self, document_id: str):
        histories = await self._load_histories()
        if document_id in histories:
            del histories[document_id]
            await self._save_histories(histories)

    async def delete_all_histories(self):
        if os.path.exists(self.file_path):
            os.remove(self.file_path)
