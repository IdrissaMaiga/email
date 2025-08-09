"""
WSGI config for email_sender project.
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'email_sender.settings')

application = get_wsgi_application()
