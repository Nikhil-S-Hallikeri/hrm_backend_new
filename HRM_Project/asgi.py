"""
ASGI config for HRM_Project.

Replaces the WSGI entry-point so Django Channels can handle both HTTP and
WebSocket connections. Required for the WhatsApp module real-time inbox.

Run with:
    daphne -b 0.0.0.0 -p 8000 HRM_Project.asgi:application

(Instead of gunicorn HRM_Project.wsgi:application)
"""
import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
import whatsapp_app.routing

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'HRM_Project.settings')

application = ProtocolTypeRouter({
    # Standard HTTP requests (all existing HRM endpoints)
    "http": get_asgi_application(),

    # WebSocket requests (WhatsApp real-time inbox)
    "websocket": AuthMiddlewareStack(
        URLRouter(
            whatsapp_app.routing.websocket_urlpatterns
        )
    ),
})
