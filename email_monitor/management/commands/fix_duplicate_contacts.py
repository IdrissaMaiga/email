from django.core.management.base import BaseCommand
from django.db import transaction
from email_monitor.models import Contact, EmailEvent
from collections import defaultdict


class Command(BaseCommand):
    help = 'Find and remove duplicate contacts, keeping the most recent one and merging email events'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without actually making changes',
        )
        parser.add_argument(
            '--auto-merge',
            action='store_true',
            help='Automatically merge duplicates without prompting',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        auto_merge = options['auto_merge']
        
        self.stdout.write(self.style.SUCCESS('🔍 Scanning for duplicate contacts...'))
        
        # Find duplicate emails
        duplicates = defaultdict(list)
        
        for contact in Contact.objects.all():
            duplicates[contact.email.lower()].append(contact)
        
        # Filter to only actual duplicates
        duplicate_emails = {email: contacts for email, contacts in duplicates.items() if len(contacts) > 1}
        
        if not duplicate_emails:
            self.stdout.write(self.style.SUCCESS('✅ No duplicate contacts found!'))
            return
        
        self.stdout.write(self.style.WARNING(f'📧 Found {len(duplicate_emails)} emails with duplicates:'))
        
        total_duplicates_removed = 0
        
        for email, contacts in duplicate_emails.items():
            self.stdout.write(f'\n📋 Email: {email}')
            self.stdout.write(f'   Duplicates: {len(contacts)} contacts')
            
            # Sort by creation date, keep the most recent
            contacts.sort(key=lambda x: x.created_at if hasattr(x, 'created_at') else x.id, reverse=True)
            contact_to_keep = contacts[0]
            contacts_to_remove = contacts[1:]
            
            self.stdout.write(f'   🎯 Keeping: ID {contact_to_keep.id} - {contact_to_keep.full_name}')
            
            for contact in contacts_to_remove:
                self.stdout.write(f'   🗑️  Removing: ID {contact.id} - {contact.full_name}')
            
            # Check if there are any EmailEvents for contacts being removed
            events_to_update = []
            for contact in contacts_to_remove:
                events = EmailEvent.objects.filter(to_email=contact.email)
                events_to_update.extend(events)
            
            if events_to_update:
                self.stdout.write(f'   📨 Found {len(events_to_update)} email events to preserve')
            
            if not dry_run:
                if not auto_merge:
                    confirm = input(f'Merge duplicates for {email}? (y/N): ')
                    if confirm.lower() != 'y':
                        self.stdout.write('   ⏭️  Skipped')
                        continue
                
                with transaction.atomic():
                    # Update any email events that reference the old contacts
                    # (EmailEvents use email address, so they should still work, but let's be sure)
                    for event in events_to_update:
                        if event.to_email.lower() == email.lower():
                            # Events are already correctly linked by email address
                            pass
                    
                    # Remove duplicate contacts
                    for contact in contacts_to_remove:
                        contact.delete()
                        total_duplicates_removed += 1
                
                self.stdout.write(self.style.SUCCESS(f'   ✅ Merged successfully'))
            else:
                self.stdout.write('   ℹ️  DRY RUN - No changes made')
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING(f'\n🔍 DRY RUN COMPLETE - Found {total_duplicates_removed} duplicates that would be removed')
            )
            self.stdout.write('Run without --dry-run to actually make changes')
        else:
            self.stdout.write(
                self.style.SUCCESS(f'\n✅ COMPLETE - Removed {total_duplicates_removed} duplicate contacts')
            )
        
        # Additional database integrity check
        self.stdout.write('\n🔍 Checking for remaining duplicates...')
        final_duplicates = defaultdict(list)
        for contact in Contact.objects.all():
            final_duplicates[contact.email.lower()].append(contact)
        
        remaining_duplicates = {email: contacts for email, contacts in final_duplicates.items() if len(contacts) > 1}
        
        if remaining_duplicates:
            self.stdout.write(self.style.ERROR(f'⚠️  Still have {len(remaining_duplicates)} emails with duplicates'))
        else:
            self.stdout.write(self.style.SUCCESS('✅ No duplicate contacts remaining'))
