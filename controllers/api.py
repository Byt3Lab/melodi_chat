import json
from quart import jsonify
from core.routing import Request, Response
from ..services.chat_service import ChatService


class ChatAPIController:
    """Contrôleur API REST pour le chat WhatsApp délégant à melodi_chat_server."""

    @staticmethod
    async def list_conversations(request: Request, response: Response):
        user_raw = request.get_session("user_payload")
        session_user = json.loads(user_raw) if isinstance(user_raw, str) else (user_raw or {})
        current_user_id = session_user.get("user_id")

        conversations = await ChatService.get_conversations(current_user_id=current_user_id)
        return jsonify({"status": "success", "conversations": conversations})

    @staticmethod
    async def direct_conversation(request: Request, response: Response):
        data = request.json or request.get_json() or {}
        target_user_id = data.get("target_user_id")
        target_username = data.get("target_username") or "Collaborateur"

        user_raw = request.get_session("user_payload")
        session_user = json.loads(user_raw) if isinstance(user_raw, str) else (user_raw or {})
        current_user_id = session_user.get("user_id")
        current_user_name = session_user.get("username") or "Admin"

        if not target_user_id:
            return jsonify({"status": "error", "message": "target_user_id requis"}), 400

        conv = await ChatService.get_or_create_direct_conversation(
            user1_id=current_user_id or "user_admin",
            user1_name=current_user_name,
            user2_id=target_user_id,
            user2_name=target_username
        )

        if not conv:
            return jsonify({"status": "error", "message": "Échec création conversation"}), 500

        return jsonify({"status": "success", "conversation": conv}), 200

    @staticmethod
    async def get_messages(request: Request, response: Response, conv_id: int = None):
        cid = (
            conv_id
            or (request.params and (request.params.get("conv_id") or request.params.get("id")))
            or (request.query and (request.query.get("conv_id") or request.query.get("conversation_id") or request.query.get("id")))
        )
        if not cid:
            return jsonify({"status": "error", "message": "conv_id requis"}), 400

        messages = await ChatService.get_messages(conversation_id=int(cid))
        return jsonify({"status": "success", "messages": messages})

    @staticmethod
    async def send_message(request: Request, response: Response):
        data = request.json or request.get_json() or {}
        conversation_id = data.get("conversation_id")
        text = (data.get("message") or "").strip()

        if not conversation_id or not text:
            return jsonify({"status": "error", "message": "Paramètres conversation_id et message requis"}), 400

        user_raw = request.get_session("user_payload")
        session_user = json.loads(user_raw) if isinstance(user_raw, str) else (user_raw or {})
        sender_id = session_user.get("user_id")
        sender_name = session_user.get("username") or "Admin"

        msg = await ChatService.send_message(
            conversation_id=int(conversation_id),
            sender_id=sender_id,
            sender_name=sender_name,
            text=text
        )

        if not msg:
            return jsonify({"status": "error", "message": "Erreur serveur chat lors de l'envoi"}), 502

        return jsonify({"status": "success", "message": msg}), 201

    @staticmethod
    async def broadcast_typing(request: Request, response: Response):
        data = request.json or request.get_json() or {}
        conversation_id = data.get("conversation_id")
        user_raw = request.get_session("user_payload")
        session_user = json.loads(user_raw) if isinstance(user_raw, str) else (user_raw or {})
        sender_id = session_user.get("user_id")
        sender_name = session_user.get("username") or "Un collaborateur"

        if conversation_id:
            await ChatService.broadcast_typing(
                conv_id=int(conversation_id),
                user_id=sender_id,
                user_name=sender_name
            )
        return jsonify({"status": "success"})

    @staticmethod
    async def create_group(request: Request, response: Response):
        data = request.json or request.get_json() or {}
        title = (data.get("title") or "").strip()
        description = (data.get("description") or "").strip()
        member_ids = data.get("member_ids") or []

        if not title:
            return jsonify({"status": "error", "message": "Le titre du groupe est requis"}), 400

        user_raw = request.get_session("user_payload")
        session_user = json.loads(user_raw) if isinstance(user_raw, str) else (user_raw or {})
        creator_id = session_user.get("user_id")
        creator_name = session_user.get("username") or "Admin"

        conv = await ChatService.create_group_conversation(
            title=title,
            description=description,
            created_by_id=creator_id,
            created_by_name=creator_name,
            member_ids=member_ids
        )

        if not conv:
            return jsonify({"status": "error", "message": "Échec création groupe"}), 500

        return jsonify({"status": "success", "conversation": conv}), 201

    @staticmethod
    async def delete_message(request: Request, response: Response, message_id: int = None):
        data = request.json or request.get_json() or {}
        mid = (
            message_id
            or (request.params and (request.params.get("message_id") or request.params.get("id")))
            or (request.query and (request.query.get("message_id") or request.query.get("id")))
            or (data and (data.get("message_id") or data.get("id")))
        )
        if not mid:
            return jsonify({"status": "error", "message": "message_id requis"}), 400

        success = await ChatService.delete_message(message_id=int(mid))
        if success:
            return jsonify({"status": "success", "message_id": int(mid)})
        return jsonify({"status": "error", "message": "Message introuvable ou erreur de suppression"}), 404

    @staticmethod
    async def delete_conversation(request: Request, response: Response, conv_id: int = None):
        data = request.json or request.get_json() or {}
        cid = (
            conv_id
            or (request.params and (request.params.get("conv_id") or request.params.get("id")))
            or (request.query and (request.query.get("conv_id") or request.query.get("conversation_id") or request.query.get("id")))
            or (data and (data.get("conversation_id") or data.get("id")))
        )
        if not cid:
            return jsonify({"status": "error", "message": "conv_id requis"}), 400

        success = await ChatService.delete_conversation(conv_id=int(cid))
        if success:
            return jsonify({"status": "success", "conversation_id": int(cid)})
        return jsonify({"status": "error", "message": "Discussion introuvable ou erreur de suppression"}), 404
