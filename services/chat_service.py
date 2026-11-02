import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from .chat_server_client import ChatServerClient

logger = logging.getLogger("melodi_chat.service")


class ChatService:
    """
    Logique métier de messagerie instantanée.
    Délègue l'intégralité du stockage, de la persistance et de la diffusion
    au microservice dédié melodi_chat_server (Port 7070).
    """

    @staticmethod
    async def get_conversations(session: AsyncSession = None, current_user_id: str | None = None) -> list[dict]:
        return await ChatServerClient.get_conversations(current_user_id=current_user_id)

    @staticmethod
    async def get_active_users(session: AsyncSession, exclude_user_id: str | None = None) -> list[dict]:
        """Récupère les utilisateurs ERP enregistrés dans MELODI."""
        try:
            from base.models.user_model import UserModel
            stmt = select(UserModel).where(UserModel.is_active == True)
            if exclude_user_id:
                stmt = stmt.where(UserModel.user_id != exclude_user_id)
            res = await session.execute(stmt)
            users = res.scalars().all()
            return [
                {
                    "user_id": u.user_id,
                    "username": u.username,
                    "first_name": getattr(u, "first_name", "") or "",
                    "last_name": getattr(u, "last_name", "") or "",
                    "avatar_url": getattr(u, "avatar_url", None)
                }
                for u in users
            ]
        except Exception as e:
            logger.warning(f"[Melodi Chat] Impossible de lister les utilisateurs ERP: {e}")
            return []

    @staticmethod
    async def get_or_create_direct_conversation(
        session: AsyncSession = None,
        user1_id: str = "",
        user1_name: str = "Admin",
        user2_id: str = "",
        user2_name: str = "Contact"
    ) -> dict | None:
        return await ChatServerClient.get_or_create_direct_conversation(
            user1_id=user1_id,
            user1_name=user1_name,
            user2_id=user2_id,
            user2_name=user2_name
        )

    @staticmethod
    async def get_messages(session: AsyncSession = None, conversation_id: int = 0, limit: int = 50) -> list[dict]:
        return await ChatServerClient.get_messages(conv_id=conversation_id, limit=limit)

    @staticmethod
    async def send_message(
        session: AsyncSession = None,
        app: any = None,
        conversation_id: int = 0,
        sender_id: str | None = None,
        sender_name: str = "Admin",
        text: str = "",
        sender_avatar: str | None = None
    ) -> dict | None:
        return await ChatServerClient.send_message(
            conv_id=conversation_id,
            sender_id=sender_id,
            sender_name=sender_name,
            text=text,
            sender_avatar=sender_avatar
        )

    @staticmethod
    async def create_group_conversation(
        session: AsyncSession = None,
        app: any = None,
        title: str = "",
        description: str | None = None,
        created_by_id: str | None = None,
        created_by_name: str = "Admin",
        member_ids: list[str] | None = None
    ) -> dict | None:
        return await ChatServerClient.create_group_conversation(
            title=title,
            description=description,
            created_by_id=created_by_id,
            created_by_name=created_by_name,
            member_ids=member_ids
        )

    @staticmethod
    async def delete_message(
        session: AsyncSession = None,
        app: any = None,
        message_id: int = 0
    ) -> bool:
        return await ChatServerClient.delete_message(msg_id=message_id)

    @staticmethod
    async def delete_conversation(
        session: AsyncSession = None,
        app: any = None,
        conv_id: int = 0
    ) -> bool:
        return await ChatServerClient.delete_conversation(conv_id=conv_id)

    @staticmethod
    async def broadcast_typing(
        conv_id: int,
        user_id: str | None,
        user_name: str
    ) -> bool:
        return await ChatServerClient.broadcast_typing(conv_id=conv_id, user_id=user_id, user_name=user_name)
