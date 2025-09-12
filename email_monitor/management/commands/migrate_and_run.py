from django.core.management.base import BaseCommand
from django.core.management import execute_from_command_line
import sys
import os


class Command(BaseCommand):
    help = 'Run migrations and then start the development server'

    def add_arguments(self, parser):
        parser.add_argument(
            '--port',
            type=int,
            default=8000,
            help='Port to run the server on (default: 8000)',
        )
        parser.add_argument(
            '--host',
            type=str,
            default='127.0.0.1',
            help='Host to bind the server to (default: 127.0.0.1)',
        )

    def handle(self, *args, **options):
        # Run migrations first
        self.stdout.write(self.style.SUCCESS('Running migrations...'))
        try:
            execute_from_command_line(['manage.py', 'makemigrations'])
            execute_from_command_line(['manage.py', 'migrate'])
            self.stdout.write(self.style.SUCCESS('Migrations completed successfully!'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Migration failed: {e}'))
            return

        # Start the development server
        host = options['host']
        port = options['port']
        self.stdout.write(self.style.SUCCESS(f'Starting server on {host}:{port}...'))
        
        try:
            execute_from_command_line(['manage.py', 'runserver', f'{host}:{port}'])
        except KeyboardInterrupt:
            self.stdout.write(self.style.SUCCESS('Server stopped.'))
