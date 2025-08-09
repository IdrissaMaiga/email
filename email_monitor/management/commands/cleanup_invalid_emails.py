from django.core.management.base import BaseCommand
from email_monitor.models import Contact
import re


class Command(BaseCommand):
    help = 'Clean up contacts with invalid email addresses'

    def handle(self, *args, **options):
        self.stdout.write('Starting cleanup of invalid email addresses...')
        
        # Define invalid email patterns
        invalid_emails = ['verified', 'empty', 'unknown', 'none', 'null', 'n/a', 'na', '']
        
        # Find contacts with literal invalid values
        literal_invalid = Contact.objects.filter(email__iregex=r'^(verified|empty|unknown|none|null|n/a|na)$')
        literal_count = literal_invalid.count()
        
        if literal_count > 0:
            self.stdout.write(f'Found {literal_count} contacts with literal invalid emails:')
            for contact in literal_invalid[:10]:  # Show first 10
                self.stdout.write(f'  - {contact.email} ({contact.first_name} {contact.last_name})')
            if literal_count > 10:
                self.stdout.write(f'  ... and {literal_count - 10} more')
        
        # Find contacts without @ or . in email
        pattern_invalid = Contact.objects.exclude(email__contains='@').union(
            Contact.objects.exclude(email__contains='.')
        )
        pattern_count = pattern_invalid.count()
        
        if pattern_count > 0:
            self.stdout.write(f'Found {pattern_count} contacts with malformed emails:')
            for contact in pattern_invalid[:10]:  # Show first 10
                self.stdout.write(f'  - {contact.email} ({contact.first_name} {contact.last_name})')
            if pattern_count > 10:
                self.stdout.write(f'  ... and {pattern_count - 10} more')
        
        # Ask for confirmation
        total_invalid = literal_count + pattern_count
        if total_invalid == 0:
            self.stdout.write(self.style.SUCCESS('No invalid emails found! Database is clean.'))
            return
        
        self.stdout.write(f'\nTotal invalid contacts to delete: {total_invalid}')
        confirm = input('Do you want to delete these contacts? (yes/no): ')
        
        if confirm.lower() in ['yes', 'y']:
            # Delete invalid contacts
            deleted_literal = literal_invalid.delete()[0] if literal_count > 0 else 0
            deleted_pattern = pattern_invalid.delete()[0] if pattern_count > 0 else 0
            
            total_deleted = deleted_literal + deleted_pattern
            self.stdout.write(
                self.style.SUCCESS(f'Successfully deleted {total_deleted} contacts with invalid emails')
            )
        else:
            self.stdout.write('Cleanup cancelled.')
