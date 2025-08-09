from django.apps import AppConfig
import os
import csv
import logging

logger = logging.getLogger(__name__)


class EmailMonitorConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'email_monitor'

    def ready(self):
        """This method is called when Django starts up"""
        # Import here to avoid circular imports
        from .models import Contact
        
        # Path to the CSV file
        csv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data.csv')
        
        if os.path.exists(csv_path):
            try:
                self.import_contacts_from_csv(csv_path, Contact)
                logger.info("Contact import check completed on server startup")
            except Exception as e:
                logger.error(f"Error importing contacts on startup: {e}")
        else:
            logger.warning(f"CSV file not found at {csv_path}")

    def import_contacts_from_csv(self, csv_path, Contact):
        """Import new contacts from CSV file"""
        imported_count = 0
        updated_count = 0
        
        with open(csv_path, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            
            for row in reader:
                # Get email from VerifiedEmail column
                email = row.get('VerifiedEmail', '').strip()
                
                if not email or email.lower() == 'empty':
                    continue
                
                # Get all fields from CSV
                first_name = row.get('prospect_first_name', '').strip()
                last_name = row.get('prospect_last_name', '').strip()
                
                # Skip if missing required fields
                if not first_name or not last_name:
                    continue
                
                # Prepare all CSV data
                csv_data = {
                    'location_city': row.get('prospect_location_city', '').strip(),
                    'location_country': row.get('prospect_location_country', '').strip(),
                    'company_name': row.get('company_name', '').strip(),
                    'company_industry': row.get('company_industry', '').strip(),
                    'company_website': row.get('company_website', '').strip(),
                    'company_description': row.get('company_description', '').strip(),
                    'company_linkedin_url': row.get('company_linkedin_url', '').strip(),
                    'company_headcount': row.get('company_headcount', '').strip(),
                    'job_title': row.get('job_title', '').strip(),
                    'linkedin_url': row.get('linkedin_url', '').strip(),
                    'linkedin_headline': row.get('linkedin_headline', '').strip(),
                    'linkedin_position': row.get('linkedin_position', '').strip(),
                    'linkedin_summary': row.get('linkedin_summary', '').strip(),
                    'phone_number': row.get('phone_number', '').strip(),
                    'tailored_tone_first_line': row.get('tailored_tone_first_line', '').strip(),
                    'tailored_tone_ps_statement': row.get('tailored_tone_ps_statement', '').strip(),
                    'tailored_tone_subject': row.get('tailored_tone_subject', '').strip(),
                    'custom_ai_1': row.get('custom_ai_1', '').strip(),
                    'custom_ai_2': row.get('custom_ai_2', '').strip(),
                    'profile_image_url': row.get('profile_image_url', '').strip(),
                    'logo_image_url': row.get('logo_image_url', '').strip(),
                    'funnel_unique_id': row.get('funnel_unique_id', '').strip(),
                    'funnel_step': row.get('funnel_step', '').strip(),
                    'sequence_unique_id': row.get('sequence_unique_id', '').strip(),
                    'variation_unique_id': row.get('variation_unique_id', '').strip(),
                    'emailsender': row.get('emailsender', '').strip(),
                    'websitecontent': row.get('websitecontent', '').strip(),
                    'leadscore': row.get('leadscore', '').strip(),
                    'esp': row.get('ESP', '').strip(),
                }
                
                # Check if contact already exists
                contact, created = Contact.objects.get_or_create(
                    email=email,
                    defaults={
                        'first_name': first_name,
                        'last_name': last_name,
                        'email_status': 'not_sent',
                        **csv_data  # Unpack all CSV data
                    }
                )
                
                if created:
                    imported_count += 1
                    logger.info(f"Imported new contact: {first_name} {last_name} ({email})")
                else:
                    # Update existing contact info if needed
                    updated = False
                    if contact.first_name != first_name:
                        contact.first_name = first_name
                        updated = True
                    if contact.last_name != last_name:
                        contact.last_name = last_name
                        updated = True
                    
                    # Update all CSV fields
                    for field_name, field_value in csv_data.items():
                        current_value = getattr(contact, field_name, '')
                        if current_value != field_value:
                            setattr(contact, field_name, field_value)
                            updated = True
                    
                    if updated:
                        contact.save()
                        updated_count += 1
                        logger.info(f"Updated contact: {first_name} {last_name} ({email})")
        
        if imported_count > 0 or updated_count > 0:
            logger.info(f"CSV import completed: {imported_count} new contacts, {updated_count} updated contacts")
        else:
            logger.info("No new contacts to import from CSV")
