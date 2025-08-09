"""
ASGI config for email_sender project.
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'email_sender.settings')

application = get_asgi_application()
