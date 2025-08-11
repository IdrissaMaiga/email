from django.apps import AppConfig
import logging

logger = logging.getLogger(__name__)


class EmailMonitorConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'email_monitor'

    def ready(self):
        """This method is called when Django starts up - CSV import disabled"""
        logger.info("Email Monitor app ready - UI-only contact management enabled")
        
        # CSV import functionality has been disabled
        # Contacts are now managed exclusively through the web UI:
        # - Create: /monitor/contacts/create/
        # - Edit: /monitor/contacts/edit/<id>/
        # - Delete: /monitor/contacts/delete/<id>/
        # - List: /monitor/contacts/
        # - CSV Upload: /monitor/contacts/upload/
        
        logger.info("CSV import disabled - use web interface to manage contacts")
