from django.core.management.commands.runserver import Command as RunserverCommand
from django.conf import settings


class Command(RunserverCommand):
    """
    Custom runserver command that uses the DEFAULT_PORT from settings.
    """
    def add_arguments(self, parser):
        super().add_arguments(parser)
        # Override the default port in the addrport argument
        for action in parser._actions:
            if hasattr(action, 'dest') and action.dest == 'addrport':
                # Set the default port from settings
                default_port = getattr(settings, 'DEFAULT_PORT', 8000)
                action.default = f'127.0.0.1:{default_port}'
                action.help = f'Optional port number, or ipaddr:port (default: 127.0.0.1:{default_port})'
                break
