#!/usr/bin/env python
import os
import django
import json

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'email_sender.settings')
django.setup()

from django.test import RequestFactory
from email_app.views import contact_stats_api

# Create a mock request
factory = RequestFactory()
request = factory.get('/api/contact-stats/', {'sender': 'horizoneurope'})

# Call the API
response = contact_stats_api(request)

# Parse and display the response
if response.status_code == 200:
    data = json.loads(response.content)
    print("=== CONTACT STATISTICS API RESPONSE ===")
    print(f"Total Contacts: {data['total_contacts']}")
    print(f"Total Email Events: {data['total_email_events']}")
    print(f"Not Sent: {data['not_sent']}")
    print(f"Sent: {data['sent']}")
    print(f"Delivered: {data['delivered']}")
    print(f"Opened: {data['opened']}")
    print(f"Clicked: {data['clicked']}")
    print(f"Bounced: {data['bounced']}")
    print(f"Failed: {data['failed']}")
    print(f"Complained: {data['complained']}")
    print(f"Sender: {data['sender']}")
    print(f"Sender Email: {data['sender_email']}")
    print("\n=== EXPLANATION ===")
    for key, explanation in data['stats_explanation'].items():
        print(f"{key}: {explanation}")
else:
    print(f"Error: {response.status_code}")
    print(response.content.decode())
