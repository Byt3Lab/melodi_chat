from __future__ import annotations
from core.module import ApplicationModule, Permission
from .controllers.api import ChatAPIController
from .controllers.web import ChatWebController
from .controllers.settings import ChatSettingsController


class MelodiChatModule(ApplicationModule):
    """
    Module de messagerie instantanée temps réel style WhatsApp pour MELODI ERP.
    Délègue l'intégralité du stockage et de la diffusion au serveur dédié melodi_chat_server (Port 7070).
    """

    def __init__(self, name: str, router_name: str):
        super().__init__(name=name, router_name=router_name)

    def _get_permissions(self) -> list[Permission]:
        return [
            Permission(self, "chat:read", "Accéder aux salons et lire les messages du chat"),
            Permission(self, "chat:write", "Envoyer des messages instantanés et participer aux discussions"),
            Permission(self, "chat:admin", "Gérer et configurer le serveur de chat dédié"),
        ]

    async def load(self):
        """Initialisation du module lors du démarrage de MELODI."""
        self._register_routes()
        self._register_navigation()

    def _register_routes(self):
        """Enregistre les routes Web d'administration et d'API."""
        # 1. Routes Web d'administration
        self.admin_router.add_route("", ChatWebController.chat_page, methods=["GET"])
        self.admin_router.add_route("/", ChatWebController.chat_page, methods=["GET"])

        # 2. Routes de configuration du serveur dédié (Port 7070 & Scalabilité)
        self.admin_router.add_route("/settings", ChatSettingsController.settings_page, methods=["GET"])
        self.admin_router.add_route("/settings", ChatSettingsController.update_settings, methods=["POST"])
        self.admin_router.add_route("/settings/test-connection", ChatSettingsController.test_connection, methods=["POST"])
        self.admin_router.add_route("/settings/test-redis", ChatSettingsController.test_redis, methods=["POST"])
        self.admin_router.add_route("/settings/test-db", ChatSettingsController.test_database, methods=["POST"])

        # 3. Routes API d'administration sous /admin/melodi_chat/*
        self.admin_router.add_route("/conversations", ChatAPIController.list_conversations, methods=["GET"])
        self.admin_router.add_route("/conversations/direct", ChatAPIController.direct_conversation, methods=["POST"])
        self.admin_router.add_route("/conversations/group", ChatAPIController.create_group, methods=["POST"])
        self.admin_router.add_route("/conversations", ChatAPIController.delete_conversation, methods=["DELETE"])
        self.admin_router.add_route("/conversations/<conv_id>", ChatAPIController.delete_conversation, methods=["DELETE"])
        self.admin_router.add_route("/conversations/delete", ChatAPIController.delete_conversation, methods=["POST"])

        self.admin_router.add_route("/messages", ChatAPIController.get_messages, methods=["GET"])
        self.admin_router.add_route("/messages/<conv_id>", ChatAPIController.get_messages, methods=["GET"])
        self.admin_router.add_route("/messages", ChatAPIController.send_message, methods=["POST"])
        self.admin_router.add_route("/messages", ChatAPIController.delete_message, methods=["DELETE"])
        self.admin_router.add_route("/messages/<message_id>", ChatAPIController.delete_message, methods=["DELETE"])
        self.admin_router.add_route("/messages/delete", ChatAPIController.delete_message, methods=["POST"])
        self.admin_router.add_route("/typing", ChatAPIController.broadcast_typing, methods=["POST"])

        # 4. Routes API REST publiques sous /api/melodi_chat/*
        self.api_router.add_route("/conversations", ChatAPIController.list_conversations, methods=["GET"])
        self.api_router.add_route("/conversations/direct", ChatAPIController.direct_conversation, methods=["POST"])
        self.api_router.add_route("/conversations/group", ChatAPIController.create_group, methods=["POST"])
        self.api_router.add_route("/conversations", ChatAPIController.delete_conversation, methods=["DELETE"])
        self.api_router.add_route("/conversations/<conv_id>", ChatAPIController.delete_conversation, methods=["DELETE"])
        self.api_router.add_route("/conversations/delete", ChatAPIController.delete_conversation, methods=["POST"])

        self.api_router.add_route("/messages", ChatAPIController.get_messages, methods=["GET"])
        self.api_router.add_route("/messages/<conv_id>", ChatAPIController.get_messages, methods=["GET"])
        self.api_router.add_route("/messages", ChatAPIController.send_message, methods=["POST"])
        self.api_router.add_route("/messages", ChatAPIController.delete_message, methods=["DELETE"])
        self.api_router.add_route("/messages/<message_id>", ChatAPIController.delete_message, methods=["DELETE"])
        self.api_router.add_route("/messages/delete", ChatAPIController.delete_message, methods=["POST"])
        self.api_router.add_route("/typing", ChatAPIController.broadcast_typing, methods=["POST"])

    def _register_navigation(self):
        """Enregistre le module sous un menu déroulant unique dans la barre de navigation admin."""
        self.register_navigation(
            id="melodi_chat_root",
            label="Melodi Chat",
            icon="name=forum&fill=%236366f1",
            url="/admin/melodi_chat",
            priority=42,
            children=[
                {"label": "Messagerie", "icon": "name=chat&fill=white", "url": "/admin/melodi_chat"},
                {"label": "Configuration", "icon": "name=settings&fill=white", "url": "/admin/melodi_chat/settings"},
            ]
        )


module = MelodiChatModule(name="melodi_chat", router_name="melodi_chat_router")
