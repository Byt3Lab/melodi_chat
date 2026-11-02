"""
Client HTTP asynchrone pour communiquer avec melodi_chat_server (Port 7070).
Toutes les données de messagerie sont déléguées exclusivement à ce microservice.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple
import httpx
from ..config import get_chat_settings

logger = logging.getLogger("melodi_chat.chat_server_client")


class ChatServerClient:
    """Interface avec l'API REST de melodi_chat_server."""

    @classmethod
    def _get_config(cls) -> Tuple[str, str]:
        settings = get_chat_settings()
        url = settings.get("server_url", "http://127.0.0.1:7070").rstrip("/")
        secret = settings.get("secret", "melodi_chat_secret_789")
        return url, secret

    @classmethod
    def _headers(cls) -> Dict[str, str]:
        _, secret = cls._get_config()
        return {
            "X-Melodi-Secret": secret,
            "Content-Type": "application/json",
        }

    @classmethod
    async def get_health(cls) -> Tuple[bool, Dict[str, Any]]:
        url, _ = cls._get_config()
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                res = await client.get(f"{url}/health")
                if res.status_code == 200:
                    return True, res.json()
                return False, {"status": "error", "code": res.status_code, "text": res.text}
        except Exception as e:
            return False, {"status": "error", "message": str(e)}

    @classmethod
    async def get_conversations(cls, current_user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        url, _ = cls._get_config()
        params = {}
        if current_user_id:
            params["user_id"] = str(current_user_id)

        try:
            async with httpx.AsyncClient(timeout=4.0) as client:
                res = await client.get(f"{url}/conversations", params=params, headers=cls._headers())
                if res.status_code == 200:
                    data = res.json()
                    return data.get("conversations", [])
                logger.error(f"[ChatServerClient] Erreur get_conversations ({res.status_code}): {res.text}")
                return []
        except Exception as e:
            logger.error(f"[ChatServerClient] Exception get_conversations: {e}")
            return []

    @classmethod
    async def get_conversation(cls, conv_id: int) -> Optional[Dict[str, Any]]:
        url, _ = cls._get_config()
        try:
            async with httpx.AsyncClient(timeout=4.0) as client:
                res = await client.get(f"{url}/conversations/{conv_id}", headers=cls._headers())
                if res.status_code == 200:
                    return res.json().get("conversation")
                return None
        except Exception as e:
            logger.error(f"[ChatServerClient] Exception get_conversation({conv_id}): {e}")
            return None

    @classmethod
    async def get_or_create_direct_conversation(
        cls,
        user1_id: str,
        user1_name: str,
        user2_id: str,
        user2_name: str
    ) -> Optional[Dict[str, Any]]:
        url, _ = cls._get_config()
        payload = {
            "current_user_id": str(user1_id),
            "current_user_name": user1_name,
            "target_user_id": str(user2_id),
            "target_user_name": user2_name
        }
        try:
            async with httpx.AsyncClient(timeout=4.0) as client:
                res = await client.post(f"{url}/conversations/direct", json=payload, headers=cls._headers())
                if res.status_code in (200, 201):
                    return res.json().get("conversation")
                logger.error(f"[ChatServerClient] Erreur direct_conv: {res.text}")
                return None
        except Exception as e:
            logger.error(f"[ChatServerClient] Exception direct_conv: {e}")
            return None

    @classmethod
    async def create_group_conversation(
        cls,
        title: str,
        description: Optional[str] = None,
        created_by_id: Optional[str] = None,
        created_by_name: str = "Admin",
        member_ids: Optional[List[str]] = None
    ) -> Optional[Dict[str, Any]]:
        url, _ = cls._get_config()
        payload = {
            "title": title,
            "description": description,
            "created_by_id": created_by_id,
            "created_by_name": created_by_name,
            "member_ids": member_ids or []
        }
        try:
            async with httpx.AsyncClient(timeout=4.0) as client:
                res = await client.post(f"{url}/conversations/group", json=payload, headers=cls._headers())
                if res.status_code in (200, 201):
                    return res.json().get("conversation")
                logger.error(f"[ChatServerClient] Erreur create_group: {res.text}")
                return None
        except Exception as e:
            logger.error(f"[ChatServerClient] Exception create_group: {e}")
            return None

    @classmethod
    async def delete_conversation(cls, conv_id: int) -> bool:
        url, _ = cls._get_config()
        try:
            async with httpx.AsyncClient(timeout=4.0) as client:
                res = await client.delete(f"{url}/conversations/{conv_id}", headers=cls._headers())
                return res.status_code == 200
        except Exception as e:
            logger.error(f"[ChatServerClient] Exception delete_conversation: {e}")
            return False

    @classmethod
    async def get_messages(cls, conv_id: int, limit: int = 50) -> List[Dict[str, Any]]:
        url, _ = cls._get_config()
        params = {"conv_id": conv_id, "limit": limit}
        try:
            async with httpx.AsyncClient(timeout=4.0) as client:
                res = await client.get(f"{url}/messages", params=params, headers=cls._headers())
                if res.status_code == 200:
                    return res.json().get("messages", [])
                logger.error(f"[ChatServerClient] Erreur get_messages: {res.text}")
                return []
        except Exception as e:
            logger.error(f"[ChatServerClient] Exception get_messages: {e}")
            return []

    @classmethod
    async def send_message(
        cls,
        conv_id: int,
        sender_id: Optional[str],
        sender_name: str,
        text: str,
        sender_avatar: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        url, _ = cls._get_config()
        payload = {
            "conversation_id": conv_id,
            "sender_id": sender_id,
            "sender_name": sender_name,
            "sender_avatar": sender_avatar,
            "message": text
        }
        try:
            async with httpx.AsyncClient(timeout=4.0) as client:
                res = await client.post(f"{url}/messages", json=payload, headers=cls._headers())
                if res.status_code in (200, 201):
                    return res.json().get("message")
                logger.error(f"[ChatServerClient] Erreur send_message: {res.text}")
                return None
        except Exception as e:
            logger.error(f"[ChatServerClient] Exception send_message: {e}")
            return None

    @classmethod
    async def delete_message(cls, msg_id: int) -> bool:
        url, _ = cls._get_config()
        try:
            async with httpx.AsyncClient(timeout=4.0) as client:
                res = await client.delete(f"{url}/messages/{msg_id}", headers=cls._headers())
                return res.status_code == 200
        except Exception as e:
            logger.error(f"[ChatServerClient] Exception delete_message: {e}")
            return False

    @classmethod
    async def broadcast_typing(cls, conv_id: int, user_id: Optional[str], user_name: str) -> bool:
        url, _ = cls._get_config()
        payload = {
            "conversation_id": conv_id,
            "user_id": user_id,
            "user_name": user_name
        }
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                res = await client.post(f"{url}/typing", json=payload, headers=cls._headers())
                return res.status_code == 200
        except Exception as e:
            logger.debug(f"[ChatServerClient] Exception typing: {e}")
            return False

    @classmethod
    async def test_database(cls, db_url: str) -> Tuple[bool, Dict[str, Any]]:
        url, _ = cls._get_config()
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                res = await client.post(f"{url}/test-db", json={"db_url": db_url}, headers=cls._headers())
                data = res.json() if res.status_code < 500 else {"message": res.text}
                return res.status_code == 200, data
        except Exception as e:
            return False, {"status": "error", "message": str(e)}

    @classmethod
    async def update_server_config(cls, payload: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
        url, _ = cls._get_config()
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                res = await client.post(f"{url}/config", json=payload, headers=cls._headers())
                data = res.json() if res.status_code < 500 else {"message": res.text}
                return res.status_code == 200, data
        except Exception as e:
            return False, {"status": "error", "message": str(e)}
