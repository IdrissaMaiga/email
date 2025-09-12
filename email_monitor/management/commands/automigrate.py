from django.core.management.base import BaseCommand
from django.core.management import execute_from_command_line
from django.apps import apps
import os


class Command(BaseCommand):
    help = 'Automatically detect model changes and run migrations'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Auto-migrating all apps...'))
        
        try:
            # Get all installed apps that have models
            installed_apps = []
            for app_config in apps.get_app_configs():
                if hasattr(app_config, 'models_module') and app_config.models_module is not None:
                    # Check if the app has a migrations directory or is a custom app
                    app_name = app_config.name
                    if not app_name.startswith('django.'):
                        installed_apps.append(app_name)
            
            # Make migrations for each app
            for app_name in installed_apps:
                self.stdout.write(f'Making migrations for {app_name}...')
                try:
                    execute_from_command_line(['manage.py', 'makemigrations', app_name])
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f'No changes for {app_name}: {e}'))
            
            # Run all migrations
            self.stdout.write(self.style.SUCCESS('Applying migrations...'))
            execute_from_command_line(['manage.py', 'migrate'])
            
            self.stdout.write(self.style.SUCCESS('All migrations completed successfully!'))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Migration failed: {e}'))
            raise e
