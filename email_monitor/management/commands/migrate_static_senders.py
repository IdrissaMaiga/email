from django.core.management.base import BaseCommand
from django.conf import settings
from email_monitor.models import EmailSender


class Command(BaseCommand):
    help = 'Migrate static EMAIL_SENDERS configuration to database EmailSender models'

    def add_arguments(self, parser):
        parser.add_argument(
            '--replace',
            action='store_true',
            help='Replace existing senders (deactivate all current senders)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be migrated without actually doing it',
        )

    def handle(self, *args, **options):
        # Sample static config for migration (since we removed it from settings)
        static_senders = {
            'horizoneurope': {
                'email': 'roland.zonai@horizoneurope.io',
                'name': 'Roland Zonai - Horizon Europe IO',
                'api_key': 're_Cs5WjBoq_KQVASjgHeJv5ru1Nkuomk3BY',
                'domain': 'horizoneurope.io',
                'webhook_url': 'sender.horizoneurope.io/webhook1/',
                'webhook_secret': 'whsec_mxDD0UTbIirVJ1//WCon4NpRz4e0jotf'
            },
            'horizon_eu': {
                'email': 'roland.zonai@horizon.eu.com',
                'name': 'Roland Zonai - Horizon EU',
                'api_key': 're_2g11XipG_PZyEkMWAkwJ2eTSMbZVbk5hz',
                'domain': 'horizon.eu.com',
                'webhook_url': 'sender.horizoneurope.io/webhook2/',
                'webhook_secret': 'whsec_tAU54drStmKUyqSmDT2An08p0m3WuvSv'
            }
        }
        
        if not static_senders:
            self.stdout.write(
                self.style.WARNING('No static senders found to migrate')
            )
            return

        if options['dry_run']:
            self.stdout.write(
                self.style.SUCCESS('DRY RUN: Would migrate the following senders:')
            )
            for key, config in static_senders.items():
                self.stdout.write(f"  - {key}: {config['name']} ({config['email']})")
            return

        created_count = 0
        updated_count = 0
        errors = []

        # If replace option is enabled, deactivate all existing senders
        if options['replace']:
            EmailSender.objects.all().update(is_active=False)
            self.stdout.write(
                self.style.WARNING('Deactivated all existing senders')
            )

        # Migrate each static sender
        for key, config in static_senders.items():
            try:
                # Validate required fields
                required_fields = ['email', 'name', 'api_key', 'domain']
                missing_fields = [field for field in required_fields if not config.get(field)]
                
                if missing_fields:
                    errors.append(f"Sender '{key}': Missing required fields: {', '.join(missing_fields)}")
                    continue

                # Check if sender with this key already exists
                sender, created = EmailSender.objects.get_or_create(
                    key=key,
                    defaults={
                        'email': config['email'],
                        'name': config['name'],
                        'api_key': config['api_key'],
                        'domain': config['domain'],
                        'webhook_url': config.get('webhook_url', ''),
                        'webhook_secret': config.get('webhook_secret', ''),
                        'is_active': True
                    }
                )

                if created:
                    created_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(f"Created new sender: {key} ({config['name']})")
                    )
                else:
                    # Update existing sender
                    sender.email = config['email']
                    sender.name = config['name']
                    sender.api_key = config['api_key']
                    sender.domain = config['domain']
                    sender.webhook_url = config.get('webhook_url', '')
                    sender.webhook_secret = config.get('webhook_secret', '')
                    sender.is_active = True
                    sender.save()
                    updated_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(f"Updated existing sender: {key} ({config['name']})")
                    )

            except Exception as e:
                errors.append(f"Sender '{key}': {str(e)}")
                self.stdout.write(
                    self.style.ERROR(f"Error migrating sender '{key}': {str(e)}")
                )

        # Summary
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('Migration completed!'))
        self.stdout.write(f"Created: {created_count}")
        self.stdout.write(f"Updated: {updated_count}")
        
        if errors:
            self.stdout.write(f"Errors: {len(errors)}")
            for error in errors:
                self.stdout.write(self.style.ERROR(f"  - {error}"))
        
        self.stdout.write('')
        self.stdout.write(
            self.style.SUCCESS(
                'Static senders have been migrated to the database. '
                'You can now manage them through the web interface.'
            )
        )
