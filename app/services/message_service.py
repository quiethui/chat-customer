"""聊天消息服务。"""

from app.repositories.mysql.records import ChatMessageRecord
from app.repositories.mysql_repository import MySQLRepository


class MessageService:
    """聊天消息业务服务。"""

    def __init__(self, repository: MySQLRepository) -> None:
        self.repository = repository

    def list_messages(self, user_id: int, session_id: str) -> list[ChatMessageRecord]:
        return self.repository.list_chat_messages(user_id, session_id)
