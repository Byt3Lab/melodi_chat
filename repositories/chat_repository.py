from datetime import datetime, timezone
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from ..models.chat_model import ChatConversationModel, ChatMessageModel


class ChatRepository:
    """Accès aux données SQL pour la messagerie temps réel."""

    @staticmethod
    async def get_conversations(session: AsyncSession, current_user_id: str | None = None) -> list[ChatConversationModel]:
        stmt = select(ChatConversationModel).order_by(
            desc(ChatConversationModel.last_message_time),
            ChatConversationModel.id
        )
        res = await session.execute(stmt)
        all_convs = list(res.scalars().all())

        if not current_user_id:
            return all_convs

        visible_convs = []
        for conv in all_convs:
            if conv.type == "channel":
                visible_convs.append(conv)
            elif conv.code.startswith("direct_"):
                if conv.code == "direct_direction":
                    visible_convs.append(conv)
                elif current_user_id in conv.code:
                    visible_convs.append(conv)
            else:
                visible_convs.append(conv)

        return visible_convs

    @staticmethod
    async def get_conversation_by_id(session: AsyncSession, conv_id: int) -> ChatConversationModel | None:
        stmt = select(ChatConversationModel).where(ChatConversationModel.id == conv_id)
        res = await session.execute(stmt)
        return res.scalar_one_or_none()

    @staticmethod
    async def get_or_create_direct_conversation(
        session: AsyncSession,
        user1_id: str,
        user1_name: str,
        user2_id: str,
        user2_name: str
    ) -> ChatConversationModel:
        sorted_ids = sorted([str(user1_id), str(user2_id)])
        code = f"direct_{sorted_ids[0]}_{sorted_ids[1]}"

        stmt = select(ChatConversationModel).where(ChatConversationModel.code == code)
        res = await session.execute(stmt)
        conv = res.scalar_one_or_none()

        if not conv:
            now = datetime.now(timezone.utc).replace(tzinfo=None)
            conv = ChatConversationModel(
                code=code,
                title=f"{user2_name}",
                type="direct",
                description=f"Discussion directe avec {user2_name}",
                last_message_text="Discussion démarrée",
                last_message_time=now,
                created_at=now
            )
            session.add(conv)
            await session.commit()
            await session.refresh(conv)

        return conv

    @staticmethod
    async def get_active_users(session: AsyncSession, exclude_user_id: str | None = None) -> list[dict]:
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
                "is_sudo": u.is_sudo,
            }
            for u in users
        ]

    @staticmethod
    async def get_messages(session: AsyncSession, conversation_id: int, limit: int = 50) -> list[ChatMessageModel]:
        stmt = select(ChatMessageModel).where(
            ChatMessageModel.conversation_id == conversation_id
        ).order_by(ChatMessageModel.id.asc()).limit(limit)
        res = await session.execute(stmt)
        return list(res.scalars().all())

    @staticmethod
    async def create_message(
        session: AsyncSession,
        conversation_id: int,
        sender_id: str | None,
        sender_name: str,
        message: str,
        sender_avatar: str | None = None
    ) -> ChatMessageModel:
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        msg = ChatMessageModel(
            conversation_id=conversation_id,
            sender_id=sender_id,
            sender_name=sender_name,
            sender_avatar=sender_avatar,
            message=message,
            status="delivered",
            created_at=now
        )
        session.add(msg)

        # Update parent conversation's last message
        conv = await ChatRepository.get_conversation_by_id(session, conversation_id)
        if conv:
            conv.last_message_text = (message[:50] + "...") if len(message) > 50 else message
            conv.last_message_time = now

        await session.commit()
        await session.refresh(msg)
        return msg

    @staticmethod
    async def create_group_conversation(
        session: AsyncSession,
        title: str,
        description: str | None = None,
        created_by_id: str | None = None,
        created_by_name: str = "Admin",
        member_ids: list[str] | None = None
    ) -> ChatConversationModel:
        """Crée une nouvelle conversation de type canal / groupe."""
        import uuid
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        code = f"group_{uuid.uuid4().hex[:10]}"
        conv = ChatConversationModel(
            code=code,
            title=title,
            type="channel",
            description=description or f"Groupe créé par {created_by_name}",
            last_message_text="Groupe créé",
            last_message_time=now,
            created_at=now
        )
        session.add(conv)
        await session.flush()

        # Message d'accueil / initial
        init_msg = ChatMessageModel(
            conversation_id=conv.id,
            sender_id=created_by_id,
            sender_name="Système",
            message=f"Le groupe « {title} » a été créé par {created_by_name}.",
            status="read",
            created_at=now
        )
        session.add(init_msg)
        await session.commit()
        await session.refresh(conv)
        return conv

    @staticmethod
    async def delete_message(session: AsyncSession, message_id: int) -> tuple[bool, int | None]:
        """Supprime un message et met à jour le dernier message de la conversation."""
        stmt = select(ChatMessageModel).where(ChatMessageModel.id == message_id)
        res = await session.execute(stmt)
        msg = res.scalar_one_or_none()
        if not msg:
            return False, None

        conv_id = msg.conversation_id
        await session.delete(msg)

        # Recalculer le dernier message de la conversation
        last_stmt = select(ChatMessageModel).where(
            ChatMessageModel.conversation_id == conv_id
        ).order_by(desc(ChatMessageModel.id)).limit(1)
        last_res = await session.execute(last_stmt)
        last_msg = last_res.scalar_one_or_none()

        conv = await ChatRepository.get_conversation_by_id(session, conv_id)
        if conv:
            if last_msg:
                conv.last_message_text = (last_msg.message[:50] + "...") if len(last_msg.message) > 50 else last_msg.message
                conv.last_message_time = last_msg.created_at
            else:
                conv.last_message_text = "Aucun message"
                conv.last_message_time = conv.created_at

        await session.commit()
        return True, conv_id

    @staticmethod
    async def delete_conversation(session: AsyncSession, conv_id: int) -> bool:
        """Supprime une discussion et tous ses messages associés."""
        from sqlalchemy import delete
        conv = await ChatRepository.get_conversation_by_id(session, conv_id)
        if not conv:
            return False

        # Supprimer les messages associés
        await session.execute(delete(ChatMessageModel).where(ChatMessageModel.conversation_id == conv_id))
        await session.delete(conv)
        await session.commit()
        return True

    @staticmethod
    async def seed_default_data(session: AsyncSession) -> int:
        """Initialise des conversations et messages de démonstration WhatsApp."""
        # Vérifier si des conversations existent déjà
        res = await session.execute(select(ChatConversationModel).limit(1))
        if res.scalar_one_or_none():
            return 0

        now = datetime.now(timezone.utc).replace(tzinfo=None)

        c1 = ChatConversationModel(
            code="general",
            title="Équipe Générale",
            type="channel",
            description="Canal de communication pour l'ensemble des collaborateurs MELODI",
            avatar_url=None,
            last_message_text="Bienvenue sur le chat temps réel !",
            last_message_time=now,
            created_at=now
        )
        c2 = ChatConversationModel(
            code="ventes",
            title="Commercial & Ventes",
            type="channel",
            description="Opportunités, devis et commandes en cours",
            avatar_url=None,
            last_message_text="Point hebdomadaire à 14h30",
            last_message_time=now,
            created_at=now
        )
        c3 = ChatConversationModel(
            code="support",
            title="Support Technique",
            type="channel",
            description="Assistance technique et résolutions d'incidents",
            avatar_url=None,
            last_message_text="Serveur WebSocket opérationnel à 100%",
            last_message_time=now,
            created_at=now
        )
        c4 = ChatConversationModel(
            code="direct_direction",
            title="Direction Générale",
            type="direct",
            description="Discussion directe avec la direction",
            avatar_url=None,
            last_message_text="Parfait, nous validons la nouvelle architecture.",
            last_message_time=now,
            created_at=now
        )

        session.add_all([c1, c2, c3, c4])
        await session.commit()

        # Seed initial messages
        m1 = ChatMessageModel(
            conversation_id=c1.id,
            sender_id=None,
            sender_name="Alexandre (Direction)",
            message="Bonjour à tous ! Ravi de tester ce module de messagerie style WhatsApp sur MELODI.",
            status="read",
            created_at=now
        )
        m2 = ChatMessageModel(
            conversation_id=c1.id,
            sender_id=None,
            sender_name="Sophie (Comptabilité)",
            message="Bonjour Alexandre ! L'interface est super fluide et les messages arrivent instantanément.",
            status="read",
            created_at=now
        )
        m3 = ChatMessageModel(
            conversation_id=c1.id,
            sender_id=None,
            sender_name="Mamadou (Logistique)",
            message="Et la persistance de 3 minutes fonctionne parfaitement lors des rechargements de page !",
            status="read",
            created_at=now
        )

        session.add_all([m1, m2, m3])
        await session.commit()
        return 4
