from django.core.management.base import BaseCommand
from django.conf import settings
from email_monitor.models import Contact
import csv
import os


class Command(BaseCommand):
    help = 'Import contacts from CSV file into the database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--csv-file',
            type=str,
            default='data.csv',
            help='Path to the CSV file (default: data.csv in project root)'
        )

    def handle(self, *args, **options):
        csv_file = options['csv_file']
        
        # If it's a relative path, make it relative to the project root
        if not os.path.isabs(csv_file):
            csv_file = os.path.join(settings.BASE_DIR, csv_file)
        
        if not os.path.exists(csv_file):
            self.stdout.write(
                self.style.ERROR(f'CSV file not found: {csv_file}')
            )
            return
        
        self.stdout.write(f'Importing contacts from: {csv_file}')
        
        created_count = 0
        updated_count = 0
        error_count = 0
        
        try:
            with open(csv_file, 'r', encoding='utf-8') as file:
                csv_reader = csv.DictReader(file)
                
                for row_num, row in enumerate(csv_reader, start=2):  # Start from 2 because row 1 is headers
                    try:
                        # Extract email from the VerifiedEmail field
                        email = row.get('VerifiedEmail', '').strip()
                        if not email:
                            self.stdout.write(
                                self.style.WARNING(f'Row {row_num}: No email found in VerifiedEmail column, skipping')
                            )
                            continue
                        
                        # Get or create contact
                        contact, created = Contact.objects.get_or_create(
                            email=email,
                            defaults={
                                'first_name': row.get('prospect_first_name', '').strip() or None,
                                'last_name': row.get('prospect_last_name', '').strip() or None,
                                'company_name': row.get('company_name', '').strip() or None,
                                'job_title': row.get('job_title', '').strip() or None,
                                'location_city': row.get('prospect_location_city', '').strip() or None,
                                'location_country': row.get('prospect_location_country', '').strip() or None,
                                'email_status': 'not_sent',  # Default status
                                'csv_data': row  # Store the complete row data
                            }
                        )
                        
                        if created:
                            created_count += 1
                            self.stdout.write(f'Created contact: {contact.email}')
                        else:
                            # Update existing contact with any new data
                            updated = False
                            if not contact.first_name and row.get('prospect_first_name', '').strip():
                                contact.first_name = row.get('prospect_first_name', '').strip()
                                updated = True
                            if not contact.last_name and row.get('prospect_last_name', '').strip():
                                contact.last_name = row.get('prospect_last_name', '').strip()
                                updated = True
                            if not contact.company_name and row.get('company_name', '').strip():
                                contact.company_name = row.get('company_name', '').strip()
                                updated = True
                            if not contact.job_title and row.get('job_title', '').strip():
                                contact.job_title = row.get('job_title', '').strip()
                                updated = True
                            if not contact.location_city and row.get('prospect_location_city', '').strip():
                                contact.location_city = row.get('prospect_location_city', '').strip()
                                updated = True
                            if not contact.location_country and row.get('prospect_location_country', '').strip():
                                contact.location_country = row.get('prospect_location_country', '').strip()
                                updated = True
                            
                            # Always update CSV data
                            contact.csv_data = row
                            updated = True
                            
                            if updated:
                                contact.save()
                                updated_count += 1
                                self.stdout.write(f'Updated contact: {contact.email}')
                    
                    except Exception as e:
                        error_count += 1
                        self.stdout.write(
                            self.style.ERROR(f'Row {row_num}: Error processing {email}: {str(e)}')
                        )
        
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error reading CSV file: {str(e)}')
            )
            return
        
        # Summary
        self.stdout.write(
            self.style.SUCCESS(
                f'\nImport completed!\n'
                f'Created: {created_count} contacts\n'
                f'Updated: {updated_count} contacts\n'
                f'Errors: {error_count} contacts\n'
                f'Total processed: {created_count + updated_count + error_count}'
            )
        )
