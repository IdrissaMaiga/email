"""
WebSocket URL routing for email monitoring
"""

from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/email-progress/(?P<session_id>\w+)/$', consumers.EmailProgressConsumer.as_asgi()),
]
