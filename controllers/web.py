import json
from core.page_builder import Page, Component
from core.routing import Request, Response
from base.components import admin_layout
from ..services.chat_service import ChatService


class ChatWebController:
    """Contrôleur Web pour l'interface de messagerie style WhatsApp."""

    @staticmethod
    async def chat_page(request: Request, response: Response):
        user_raw = request.get_session("user_payload")
        session_user = json.loads(user_raw) if isinstance(user_raw, str) else (user_raw or {})
        current_user_id = session_user.get("user_id")
        current_user_name = session_user.get("username") or "Admin"

        conversations = await ChatService.get_conversations(current_user_id=current_user_id)
        
        async with request.module.app.db.get_session() as session:
            users = await ChatService.get_active_users(session, exclude_user_id=current_user_id)

        initial_messages = []
        selected_conv = conversations[0] if conversations else None
        if selected_conv:
            initial_messages = await ChatService.get_messages(conversation_id=selected_conv["id"])

        content = Component(
            module_name="melodi_chat",
            name="chat_view",
            context={
                "conversations": conversations,
                "users": users,
                "selected_conv": selected_conv,
                "initial_messages": initial_messages,
                "current_user_id": current_user_id,
                "current_user_name": current_user_name,
            }
        )

        page = Page("Melodi Chat", admin_layout(content))
        return await response.render_page(page)
