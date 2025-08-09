#!/bin/bash

# Wait for database to be ready
echo "Waiting for database..."
while ! nc -z db 5432; do
  sleep 0.1
done
echo "Database is ready!"

# Run migrations
echo "Running database migrations..."
python manage.py migrate

# Load CSV data automatically
echo "Loading CSV data..."
python manage.py shell -c "
from email_app.models import Contact
import pandas as pd
import os
from django.conf import settings

csv_file_path = getattr(settings, 'CSV_FILE_PATH', 'data.csv')
if os.path.exists(csv_file_path):
    try:
        df = pd.read_csv(csv_file_path)
        df = df.fillna('')
        
        contacts_created = 0
        for _, row in df.iterrows():
            contact_data = {
                'prospect_first_name': row.get('prospect_first_name', ''),
                'prospect_last_name': row.get('prospect_last_name', ''),
                'prospect_email': row.get('prospect_email', ''),
                'job_title': row.get('job_title', ''),
                'company_name': row.get('company_name', ''),
                'prospect_location_country': row.get('prospect_location_country', ''),
                'prospect_location_continent': row.get('prospect_location_continent', ''),
                'prospect_location_region': row.get('prospect_location_region', ''),
                'prospect_company_founded_year': row.get('prospect_company_founded_year', ''),
                'prospect_company_total_funding': row.get('prospect_company_total_funding', ''),
                'company_hq_location': row.get('company_hq_location', ''),
                'company_operating_status': row.get('company_operating_status', ''),
                'prospect_company_number_of_employees': row.get('prospect_company_number_of_employees', ''),
                'prospect_company_website': row.get('prospect_company_website', ''),
                'prospect_linkedin_url': row.get('prospect_linkedin_url', ''),
                'prospect_company_linkedin_url': row.get('prospect_company_linkedin_url', ''),
                'last_job_title': row.get('last_job_title', ''),
                'last_company_name': row.get('last_company_name', ''),
                'last_company_website': row.get('last_company_website', ''),
                'last_company_linkedin_url': row.get('last_company_linkedin_url', ''),
                'prospect_location_metro': row.get('prospect_location_metro', ''),
                'company_hq_metro': row.get('company_hq_metro', ''),
                'company_latest_funding_amount': row.get('company_latest_funding_amount', ''),
                'company_latest_funding_date': row.get('company_latest_funding_date', ''),
                'company_latest_funding_round': row.get('company_latest_funding_round', ''),
                'prospect_lists': row.get('prospect_lists', ''),
                'sent_timestamp': None,
                'email_status': 'not_sent'
            }
            
            contact, created = Contact.objects.get_or_create(
                prospect_email=contact_data['prospect_email'],
                defaults=contact_data
            )
            if created:
                contacts_created += 1
        
        print(f'CSV import completed. {contacts_created} new contacts created.')
    except Exception as e:
        print(f'Error importing CSV: {str(e)}')
else:
    print('CSV file not found, skipping import.')
"

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput

# Start the server
echo "Starting server..."
if [ "$DJANGO_DEBUG" = "False" ]; then
    echo "Starting production server with Gunicorn..."
    gunicorn --bind 0.0.0.0:8000 --workers 3 email_sender.wsgi:application
else
    echo "Starting development server..."
    python manage.py runserver 0.0.0.0:8000
fi
