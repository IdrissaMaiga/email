"""
ASGI config for email_sender project.
Supports both HTTP and WebSocket connections.
"""

import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
import email_monitor.routing

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'email_sender.settings')

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter(
            email_monitor.routing.websocket_urlpatterns
        )
    ),
})
