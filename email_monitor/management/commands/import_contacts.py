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
                                'company_industry': row.get('company_industry', '').strip() or None,
                                'company_website': row.get('company_website', '').strip() or None,
                                'company_description': row.get('company_description', '').strip() or None,
                                'company_linkedin_url': row.get('company_linkedin_url', '').strip() or None,
                                'company_headcount': row.get('company_headcount', '').strip() or None,
                                'job_title': row.get('job_title', '').strip() or None,
                                'linkedin_url': row.get('linkedin_url', '').strip() or None,
                                'linkedin_headline': row.get('linkedin_headline', '').strip() or None,
                                'linkedin_position': row.get('linkedin_position', '').strip() or None,
                                'linkedin_summary': row.get('linkedin_summary', '').strip() or None,
                                'phone_number': row.get('phone_number', '').strip() or None,
                                'location_city': row.get('prospect_location_city', '').strip() or None,
                                'location_country': row.get('prospect_location_country', '').strip() or None,
                                'tailored_tone_first_line': row.get('tailored_tone_first_line', '').strip() or None,
                                'tailored_tone_ps_statement': row.get('tailored_tone_ps_statement', '').strip() or None,
                                'tailored_tone_subject': row.get('tailored_tone_subject', '').strip() or None,
                                'custom_ai_1': row.get('custom_ai_1', '').strip() or None,
                                'custom_ai_2': row.get('custom_ai_2', '').strip() or None,
                                'profile_image_url': row.get('profile_image_url', '').strip() or None,
                                'logo_image_url': row.get('logo_image_url', '').strip() or None,
                                'funnel_unique_id': row.get('funnel_unique_id', '').strip() or None,
                                'funnel_step': row.get('funnel_step', '').strip() or None,
                                'sequence_unique_id': row.get('sequence_unique_id', '').strip() or None,
                                'variation_unique_id': row.get('variation_unique_id', '').strip() or None,
                                'emailsender': row.get('emailsender', '').strip() or None,
                                'websitecontent': row.get('websitecontent', '').strip() or None,
                                'leadscore': row.get('leadscore', '').strip() or None,
                                'esp': row.get('ESP', '').strip() or None,
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
                            update_fields = [
                                ('first_name', 'prospect_first_name'),
                                ('last_name', 'prospect_last_name'),
                                ('company_name', 'company_name'),
                                ('company_industry', 'company_industry'),
                                ('company_website', 'company_website'),
                                ('company_description', 'company_description'),
                                ('company_linkedin_url', 'company_linkedin_url'),
                                ('company_headcount', 'company_headcount'),
                                ('job_title', 'job_title'),
                                ('linkedin_url', 'linkedin_url'),
                                ('linkedin_headline', 'linkedin_headline'),
                                ('linkedin_position', 'linkedin_position'),
                                ('linkedin_summary', 'linkedin_summary'),
                                ('phone_number', 'phone_number'),
                                ('location_city', 'prospect_location_city'),
                                ('location_country', 'prospect_location_country'),
                                ('tailored_tone_first_line', 'tailored_tone_first_line'),
                                ('tailored_tone_ps_statement', 'tailored_tone_ps_statement'),
                                ('tailored_tone_subject', 'tailored_tone_subject'),
                                ('custom_ai_1', 'custom_ai_1'),
                                ('custom_ai_2', 'custom_ai_2'),
                                ('profile_image_url', 'profile_image_url'),
                                ('logo_image_url', 'logo_image_url'),
                                ('funnel_unique_id', 'funnel_unique_id'),
                                ('funnel_step', 'funnel_step'),
                                ('sequence_unique_id', 'sequence_unique_id'),
                                ('variation_unique_id', 'variation_unique_id'),
                                ('emailsender', 'emailsender'),
                                ('websitecontent', 'websitecontent'),
                                ('leadscore', 'leadscore'),
                                ('esp', 'ESP'),
                            ]
                            
                            for model_field, csv_field in update_fields:
                                current_value = getattr(contact, model_field)
                                new_value = row.get(csv_field, '').strip() or None
                                if not current_value and new_value:
                                    setattr(contact, model_field, new_value)
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
