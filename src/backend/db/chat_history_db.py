from typing import List, Dict, Optional
from sqlalchemy import select, delete
from backend.db.database import db_client, DBChat, DBMessage


class ChatHistoryManagerDB:
    """Database-based chat history manager using PostgreSQL."""

    def __init__(self):
        pass

    async def create_chat(
        self, chat_name: str = "Untitled Chat", document_id: str = None
    ) -> int:
        """Create a new chat and return the chat ID."""
        async with db_client() as session:
            chat = DBChat(chat_name=chat_name, document_id=document_id)
            session.add(chat)
            await session.commit()
            await session.refresh(chat)
            return chat.id

    async def update_chat_name(self, chat_id: int, chat_name: str):
        """Update the chat name."""
        async with db_client() as session:
            result = await session.execute(select(DBChat).where(DBChat.id == chat_id))
            chat = result.scalar_one_or_none()
            if chat:
                chat.chat_name = chat_name
                await session.commit()

    async def get_chat(self, chat_id: int) -> Optional[Dict]:
        """Get a chat by ID."""
        async with db_client() as session:
            result = await session.execute(select(DBChat).where(DBChat.id == chat_id))
            chat = result.scalar_one_or_none()
            if chat:
                return chat.to_dict()
            return None

    async def get_chat_by_document_id(self, document_id: str) -> Optional[Dict]:
        """Get a chat by document_id."""
        async with db_client() as session:
            result = await session.execute(
                select(DBChat).where(DBChat.document_id == document_id)
            )
            chat = result.scalar_one_or_none()
            if chat:
                try:
                    return {
                        "id": chat.id,
                        "created_at": chat.created_at.isoformat()
                        if chat.created_at
                        else None,
                        "updated_at": chat.updated_at.isoformat()
                        if chat.updated_at
                        else None,
                        "chat_name": chat.chat_name,
                        "document_id": chat.document_id,
                    }
                except Exception as e:
                    print(f"Error converting chat to dict: {e}")
                    return None
            return None

    async def get_all_chats(self) -> List[Dict]:
        """Get all chats ordered by updated_at descending."""
        async with db_client() as session:
            result = await session.execute(
                select(DBChat).order_by(DBChat.updated_at.desc())
            )
            chats = result.scalars().all()
            return [chat.to_dict() for chat in chats]

    async def delete_chat(self, chat_id: int) -> bool:
        """Delete a chat and all its messages."""
        async with db_client() as session:
            result = await session.execute(select(DBChat).where(DBChat.id == chat_id))
            chat = result.scalar_one_or_none()
            if chat:
                await session.delete(chat)
                await session.commit()
                return True
            return False

    async def add_message(
        self, chat_id: int, role: str, content: str
    ) -> Optional[Dict]:
        """Add a message to a chat."""
        async with db_client() as session:
            result = await session.execute(select(DBChat).where(DBChat.id == chat_id))
            chat = result.scalar_one_or_none()
            if not chat:
                return None

            message = DBMessage(chat_id=chat_id, role=role, content=content)
            session.add(message)
            await session.commit()
            await session.refresh(message)
            return message.to_dict()

    async def get_messages(self, chat_id: int) -> List[Dict]:
        """Get all messages for a chat ordered by created_at."""
        async with db_client() as session:
            result = await session.execute(
                select(DBMessage)
                .where(DBMessage.chat_id == chat_id)
                .order_by(DBMessage.created_at)
            )
            messages = result.scalars().all()
            return [msg.to_dict() for msg in messages]

    async def get_chat_history_for_llm(self, chat_id: int) -> List[Dict[str, str]]:
        """Get chat history formatted for LLM consumption."""
        messages = await self.get_messages(chat_id)
        return [{"role": msg["role"], "content": msg["content"]} for msg in messages]

    async def clear_messages(self, chat_id: int) -> bool:
        """Clear all messages from a chat."""
        async with db_client() as session:
            result = await session.execute(select(DBChat).where(DBChat.id == chat_id))
            chat = result.scalar_one_or_none()
            if not chat:
                return False

            await session.execute(delete(DBMessage).where(DBMessage.chat_id == chat_id))
            await session.commit()
            return True

    async def get_history(self, document_id: str) -> List[Dict]:
        """Legacy method: Get history by document_id (treated as chat_id)."""
        try:
            chat_id = int(document_id)
            return await self.get_chat_history_for_llm(chat_id)
        except ValueError:
            return []

    async def save_history(self, document_id: str, history: List[Dict]):
        """Legacy method: Save history by document_id."""
        try:
            chat_id = int(document_id)
            await self.clear_messages(chat_id)
            for msg in history:
                if msg.get("role") in ["user", "assistant", "system"]:
                    await self.add_message(chat_id, msg["role"], msg["content"])
        except ValueError:
            pass

    async def add_message_legacy(self, document_id: str, role: str, content: str):
        """Legacy method: Add message by document_id."""
        try:
            chat_id = int(document_id)
            await self.add_message(chat_id, role, content)
        except ValueError:
            pass

    async def clear_history(self, document_id: str):
        """Legacy method: Clear history by document_id."""
        try:
            chat_id = int(document_id)
            await self.clear_messages(chat_id)
        except ValueError:
            pass

    async def delete_all_histories(self):
        """Delete all chats and messages."""
        async with db_client() as session:
            await session.execute(delete(DBMessage))
            await session.execute(delete(DBChat))
            await session.commit()
