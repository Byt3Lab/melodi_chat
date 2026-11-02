import json
from quart import jsonify
from core.page_builder import Page, Component
from core.routing import Request, Response
from base.components import admin_layout
from ..config import get_chat_settings, save_chat_settings, build_db_url
from ..services.chat_server_client import ChatServerClient


class ChatSettingsController:
    """Contrôleur pour la gestion et la configuration de melodi_chat_server."""

    @staticmethod
    async def settings_page(request: Request, response: Response):
        settings = get_chat_settings()
        is_healthy, health_info = await ChatServerClient.get_health()

        content = Component(
            module_name="melodi_chat",
            name="chat_settings",
            context={
                "settings": settings,
                "is_healthy": is_healthy,
                "health_info": health_info if is_healthy else {},
            }
        )

        page = Page("Configuration du Serveur de Chat", admin_layout(content))
        return await response.render_page(page)

    @staticmethod
    async def update_settings(request: Request, response: Response):
        data = request.json or request.get_json() or {}
        if not data and hasattr(request, "form"):
            form = await request.form
            data = dict(form)

        new_settings = {}
        text_keys = [
            "server_url", "secret", "scale_mode",
            "redis_host", "redis_password",
            "db_type", "db_name", "db_host", "db_user", "db_password", "db_custom_url"
        ]
        for key in text_keys:
            if key in data:
                new_settings[key] = str(data[key]).strip()

        if "redis_port" in data:
            try:
                new_settings["redis_port"] = int(data["redis_port"])
            except (ValueError, TypeError):
                pass

        if "db_port" in data:
            try:
                new_settings["db_port"] = int(data["db_port"])
            except (ValueError, TypeError):
                pass

        # 1. Sauvegarde locale des paramètres
        saved = save_chat_settings(new_settings)

        # 2. Propagation vers melodi_chat_server
        target_db_url = build_db_url(saved)
        server_payload = {
            "db_url": target_db_url,
            "scale_mode": saved.get("scale_mode", "autonome"),
            "redis_host": saved.get("redis_host", "localhost"),
            "redis_port": saved.get("redis_port", 6379),
            "redis_password": saved.get("redis_password", "")
        }
        ok, res = await ChatServerClient.update_server_config(server_payload)

        msg = "Configuration enregistrée."
        if ok:
            msg += f" Base de données synchronisée ({res.get('db_type', 'SQL')})."
        else:
            msg += f" Note: Le microservice melodi_chat_server n'a pas pu appliquer la configuration immédiatement ({res.get('message', 'inaccessible')})."

        return jsonify({
            "status": "success" if ok else "warning",
            "message": msg,
            "settings": saved,
            "server_response": res
        })

    @staticmethod
    async def test_connection(request: Request, response: Response):
        is_healthy, health_info = await ChatServerClient.get_health()
        if is_healthy:
            return jsonify({
                "status": "success",
                "message": "Connexion établie avec succès avec melodi_chat_server (Port 7070)",
                "data": health_info
            })
        return jsonify({
            "status": "error",
            "message": "Impossible de contacter melodi_chat_server sur le port configuré",
            "details": health_info
        }), 502

    @staticmethod
    async def test_database(request: Request, response: Response):
        data = request.json or request.get_json() or {}
        if not data and hasattr(request, "form"):
            form = await request.form
            data = dict(form)

        settings = get_chat_settings()
        settings.update(data)
        db_url = build_db_url(settings)

        ok, res = await ChatServerClient.test_database(db_url)
        if ok:
            return jsonify({
                "status": "success",
                "message": res.get("message", "Connexion à la base réussie"),
                "db_type": res.get("db_type"),
                "db_url_masked": res.get("db_url_masked")
            })
        return jsonify({
            "status": "error",
            "message": res.get("message", "Impossible de se connecter à la base de données spécifiée")
        }), 400

    @staticmethod
    async def test_redis(request: Request, response: Response):
        import redis.asyncio as aioredis
        settings = get_chat_settings()
        host = settings.get("redis_host", "localhost")
        port = settings.get("redis_port", 6379)
        password = settings.get("redis_password") or ""

        try:
            client = aioredis.Redis(host=host, port=port, password=password or None, socket_timeout=2.0)
            res = await client.ping()
            await client.aclose()
            if res:
                return jsonify({
                    "status": "success",
                    "message": f"Cluster Redis opérationnel sur {host}:{port}"
                })
        except Exception as e:
            return jsonify({
                "status": "error",
                "message": f"Échec de connexion Redis sur {host}:{port}: {str(e)}"
            }), 502
