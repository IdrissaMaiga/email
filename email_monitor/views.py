from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.conf import settings
from django.utils import timezone
from django.db.models import Count, Q
from django.core.paginator import Paginator
from django.contrib import messages
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.core.exceptions import RequestDataTooBig
from .models import EmailEvent, EmailCampaign, Contact
from .forms import ContactForm, ContactSearchForm, CSVUploadForm
import json
import csv
import io
import hashlib
import hmac
import logging

logger = logging.getLogger(__name__)


def dashboard(request):
    """Main dashboard view with contact statistics from CSV"""
    
    # Get contact statistics
    total_contacts = Contact.objects.count()
    not_sent_count = Contact.objects.filter(email_status='not_sent').count()
    sent_count = Contact.objects.filter(email_status='sent').count()
    delivered_count = Contact.objects.filter(email_status='delivered').count()
    opened_count = Contact.objects.filter(email_status='opened').count()
    clicked_count = Contact.objects.filter(email_status='clicked').count()
    bounced_count = Contact.objects.filter(email_status='bounced').count()
    failed_count = Contact.objects.filter(email_status='failed').count()
    complained_count = Contact.objects.filter(email_status='complained').count()
    
    # Calculate rates
    delivery_rate = round((delivered_count / sent_count * 100), 2) if sent_count > 0 else 0
    open_rate = round((opened_count / delivered_count * 100), 2) if delivered_count > 0 else 0
    click_rate = round((clicked_count / delivered_count * 100), 2) if delivered_count > 0 else 0
    bounce_rate = round((bounced_count / sent_count * 100), 2) if sent_count > 0 else 0
    
    # Get recent contacts (last 20)
    recent_contacts = Contact.objects.all()[:20]
    
    # Get status distribution for chart
    contact_stats = [
        {'status': 'Not Sent', 'count': not_sent_count},
        {'status': 'Sent', 'count': sent_count},
        {'status': 'Delivered', 'count': delivered_count},
        {'status': 'Opened', 'count': opened_count},
        {'status': 'Clicked', 'count': clicked_count},
        {'status': 'Bounced', 'count': bounced_count},
        {'status': 'Failed', 'count': failed_count},
        {'status': 'Complained', 'count': complained_count},
    ]
    # Remove zero counts for cleaner chart
    contact_stats = [stat for stat in contact_stats if stat['count'] > 0]
    
    context = {
        'recent_contacts': recent_contacts,
        'contact_stats': contact_stats,
        'stats': {
            'total_contacts': total_contacts,
            'not_sent_count': not_sent_count,
            'sent_count': sent_count,
            'delivered_count': delivered_count,
            'opened_count': opened_count,
            'clicked_count': clicked_count,
            'bounced_count': bounced_count,
            'failed_count': failed_count,
            'complained_count': complained_count,
            'delivery_rate': delivery_rate,
            'open_rate': open_rate,
            'click_rate': click_rate,
            'bounce_rate': bounce_rate,
        }
    }
    
    return render(request, 'email_monitor/dashboard.html', context)


def contacts_list(request):
    """View to display all contacts from CSV with their email status"""
    
    # Filter by status if specified
    status_filter = request.GET.get('status')
    contacts = Contact.objects.all()
    
    if status_filter:
        contacts = contacts.filter(email_status=status_filter)
    
    # Search by name or email
    search = request.GET.get('search')
    if search:
        contacts = contacts.filter(
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search) |
            Q(email__icontains=search) |
            Q(company_name__icontains=search)
        )
    
    # Sorting
    sort_by = request.GET.get('sort_by')
    if sort_by == 'name_asc':
        contacts = contacts.order_by('first_name', 'last_name')
    elif sort_by == 'name_desc':
        contacts = contacts.order_by('-first_name', '-last_name')
    elif sort_by == 'id_asc':
        contacts = contacts.order_by('id')
    elif sort_by == 'id_desc':
        contacts = contacts.order_by('-id')
    elif sort_by == 'date_asc':
        contacts = contacts.order_by('created_at')
    elif sort_by == 'date_desc':
        contacts = contacts.order_by('-created_at')
    elif sort_by == 'email_asc':
        contacts = contacts.order_by('email')
    elif sort_by == 'email_desc':
        contacts = contacts.order_by('-email')
    else:
        # Default ordering by creation date (newest first)
        contacts = contacts.order_by('-created_at')
    
    # Pagination
    paginator = Paginator(contacts, 50)  # Show 50 contacts per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get status counts for the filter buttons
    status_counts = {}
    for status_code, status_name in Contact.EMAIL_STATUS_CHOICES:
        status_counts[status_code] = Contact.objects.filter(email_status=status_code).count()
    
    context = {
        'page_obj': page_obj,
        'status_counts': status_counts,
        'current_status': status_filter,
        'current_search': search,
        'current_sort': sort_by,
        'status_choices': Contact.EMAIL_STATUS_CHOICES,
    }
    
    return render(request, 'email_monitor/contacts_list.html', context)


@csrf_exempt
def contact_email_content_api(request):
    """API endpoint to get email content for a specific contact"""
    email = request.GET.get('email')
    if not email:
        return JsonResponse({'error': 'Email parameter is required'}, status=400)
    
    try:
        # Get the contact
        contact = Contact.objects.get(email=email)
        
        # Find the most recent email event for this contact
        recent_event = EmailEvent.objects.filter(
            to_email=email,
            event_type__in=['email.sent', 'email.delivered', 'email.opened', 'email.clicked']
        ).order_by('-created_at').first()
        
        if not recent_event:
            return JsonResponse({'error': 'No email found for this contact'}, status=404)
        
        # Get email_id from the event
        email_id = recent_event.email_id
        if not email_id:
            return JsonResponse({'error': 'Email ID not found in event data'}, status=404)
        
        # Fetch email content from Resend API
        import requests
        import os
        
        # Determine which API key to use based on the sender
        # First try to get the sender from the recent event
        from_email = recent_event.from_email if recent_event.from_email else ''
        
        # Get the appropriate API key based on sender email
        email_senders = getattr(settings, 'EMAIL_SENDERS', {})
        resend_api_key = None
        
        if 'roland.zonai@horizoneurope.io' in from_email:
            resend_api_key = email_senders.get('horizoneurope', {}).get('api_key')
        elif 'roland.zonai@horizon.eu.com' in from_email:
            resend_api_key = email_senders.get('horizon_eu', {}).get('api_key')
        
        # Fallback to environment variable if no match found
        if not resend_api_key:
            resend_api_key = os.getenv('RESEND_API_KEY')
            # If still no API key, try the first available one
            if not resend_api_key and email_senders:
                first_sender = list(email_senders.values())[0]
                resend_api_key = first_sender.get('api_key')
        
        if not resend_api_key:
            return JsonResponse({'error': 'Resend API key not configured'}, status=500)
        
        # Make request to Resend API to get email content
        headers = {
            'Authorization': f'Bearer {resend_api_key}',
            'Content-Type': 'application/json'
        }
        
        # Use Resend's emails API to get email details
        resend_url = f'https://api.resend.com/emails/{email_id}'
        response = requests.get(resend_url, headers=headers)
        
        if response.status_code == 200:
            email_data = response.json()
            
            # Extract content from Resend API response
            html_content = email_data.get('html')
            text_content = email_data.get('text')
            subject = email_data.get('subject')
            sent_date = email_data.get('created_at')
            
            # Format the response
            response_data = {
                'to_email': email,
                'subject': subject or 'No subject',
                'sent_date': sent_date,
                'status': contact.display_status,
                'html_content': html_content,
                'text_content': text_content,
                'event_type': recent_event.event_type,
                'email_id': email_id
            }
            
            return JsonResponse(response_data)
        else:
            return JsonResponse({
                'error': f'Failed to fetch email from Resend API: {response.status_code} - {response.text}'
            }, status=500)
        
    except Contact.DoesNotExist:
        return JsonResponse({'error': 'Contact not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': f'Failed to retrieve email content: {str(e)}'}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def webhook_endpoint_1(request):
    """
    Webhook endpoint for roland.zonai@horizoneurope.io
    URL: sender.horizoneurope.io/webhook1
    """
    return webhook_handler(request, 'horizoneurope')

@csrf_exempt
@require_http_methods(["POST"])
def webhook_endpoint_2(request):
    """
    Webhook endpoint for roland.zonai@horizon.eu.com
    URL: sender.horizoneurope.io/webhook2
    """
    return webhook_handler(request, 'horizon_eu')

def webhook_handler(request, sender_key):
    """
    Common webhook handler for all sender configurations
    """
    try:
        # Get sender configuration
        email_senders = getattr(settings, 'EMAIL_SENDERS', {})
        if sender_key not in email_senders:
            logger.error(f"Invalid sender key: {sender_key}")
            return HttpResponse(status=400)
        
        sender_config = email_senders[sender_key]
        webhook_secret = sender_config.get('webhook_secret')
        
        if not webhook_secret:
            logger.error(f"No webhook secret configured for sender: {sender_key}")
            return HttpResponse(status=400)
        
        # Verify webhook signature
        if not verify_webhook_signature(request, webhook_secret):
            logger.error(f"Invalid webhook signature for sender: {sender_key}")
            return HttpResponse(status=403)
        
        # Parse webhook payload
        raw_body = request.body.decode('utf-8')
        payload = json.loads(raw_body)
        
        # Log the full payload for debugging
        logger.info(f"Received webhook payload for {sender_key}: {payload}")
        
        event_type = payload.get('type')
        data = payload.get('data', {})
        
        # Extract event_id - Resend sends email_id in data object, not top-level id
        event_id = data.get('email_id', '') or payload.get('id', '')
        
        # Extract common fields
        event_data = {
            'event_id': event_id,
            'event_type': event_type,
            'created_at': timezone.now(),  # Use current time if not provided
            'raw_data': payload,
        }
        
        # Extract event-specific data based on type
        if event_type and event_type.startswith('email.'):
            email_data = data
            event_data.update({
                'email_id': email_data.get('email_id'),
                'from_email': email_data.get('from'),
                'to_email': None,  # Will extract safely below
                'subject': email_data.get('subject'),
            })
            
            # Safely extract to_email
            to_field = email_data.get('to')
            if to_field:
                if isinstance(to_field, list) and len(to_field) > 0:
                    # Handle array format: ["email@example.com"] or [{"email": "email@example.com"}]
                    first_recipient = to_field[0]
                    if isinstance(first_recipient, dict):
                        event_data['to_email'] = first_recipient.get('email')
                    else:
                        event_data['to_email'] = str(first_recipient)
                elif isinstance(to_field, str):
                    event_data['to_email'] = to_field
            
            # Event-specific fields based on Resend webhook documentation
            if event_type == 'email.clicked':
                click_data = email_data.get('click', {})
                if isinstance(click_data, dict):
                    event_data['click_url'] = click_data.get('link')  # Resend uses 'link' not 'url'
                    
            elif event_type == 'email.bounced':
                bounce_data = email_data.get('bounce', {})
                if isinstance(bounce_data, dict):
                    # Combine bounce type, subType and message for full context
                    bounce_parts = []
                    if bounce_data.get('type'):
                        bounce_parts.append(f"Type: {bounce_data['type']}")
                    if bounce_data.get('subType'):
                        bounce_parts.append(f"SubType: {bounce_data['subType']}")
                    if bounce_data.get('message'):
                        bounce_parts.append(f"Message: {bounce_data['message']}")
                    event_data['bounce_reason'] = ' | '.join(bounce_parts) if bounce_parts else None
                    
            elif event_type == 'email.complained':
                # For complaints, Resend doesn't seem to provide specific feedback_type in their docs
                # So we'll just mark it as a complaint
                event_data['complaint_feedback_type'] = 'spam'
                
            elif event_type == 'email.failed':
                failed_data = email_data.get('failed', {})
                if isinstance(failed_data, dict):
                    event_data['bounce_reason'] = failed_data.get('reason')  # Reuse bounce_reason field for failed reason
        
        # Create event record (allow duplicates)
        event = EmailEvent.objects.create(**event_data)
        
        # Update contact status based on email event
        if event_data.get('to_email'):
            try:
                contact = Contact.objects.get(email=event_data['to_email'])
                
                # Update contact status based on event type
                if event_type == 'email.delivered':
                    contact.email_status = 'delivered'
                elif event_type == 'email.opened':
                    contact.email_status = 'opened'
                    contact.last_opened = timezone.now()
                elif event_type == 'email.clicked':
                    contact.email_status = 'clicked'
                    contact.last_clicked = timezone.now()
                elif event_type in ['email.bounced', 'email.failed']:
                    contact.email_status = 'bounced' if event_type == 'email.bounced' else 'failed'
                elif event_type == 'email.complained':
                    contact.email_status = 'complained'
                
                contact.save()
            except Contact.DoesNotExist:
                # Contact doesn't exist, could be from external emails
                pass
        
        logger.info(f"New webhook event: {event_type} for {event_data.get('to_email')}")
        
        return JsonResponse({
            'status': 'success',
            'event_id': event_data['event_id'],
            'created': True
        })
        
    except json.JSONDecodeError:
        logger.error("Invalid JSON in webhook payload")
        return HttpResponse("Invalid JSON", status=400)
    except Exception as e:
        logger.error(f"Webhook processing error: {str(e)}")
        return HttpResponse(f"Error processing webhook: {str(e)}", status=500)


def verify_webhook_signature(request, signing_secret):
    """Verify Resend webhook signature using Svix format"""
    try:
        # Resend uses Svix for webhooks, so check for svix headers
        svix_id = request.headers.get('svix-id')
        svix_timestamp = request.headers.get('svix-timestamp')
        svix_signature = request.headers.get('svix-signature')
        
        if not all([svix_id, svix_timestamp, svix_signature]):
            logger.error("Missing svix headers - found headers: " + str(dict(request.headers)))
            return False
        
        # Log signature details for debugging (minimal logging)
        logger.debug(f"Svix ID: {svix_id}")
        logger.debug(f"Svix Timestamp: {svix_timestamp}")
        logger.debug(f"Webhook secret: {signing_secret[:10]}...") # Only log first 10 chars for security
        
        # Remove the whsec_ prefix from the signing secret if present
        if signing_secret.startswith('whsec_'):
            secret_key = signing_secret[6:]  # Remove 'whsec_' prefix
        else:
            secret_key = signing_secret
        
        logger.debug(f"Secret key after prefix removal: {secret_key[:10]}...") # Only log first 10 chars
        
        # Create the signed payload using Svix format
        # Format: {id}.{timestamp}.{payload}
        payload = request.body.decode('utf-8')
        signed_payload = f"{svix_id}.{svix_timestamp}.{payload}"
        
        logger.debug(f"Signed payload length: {len(signed_payload)} chars")
        
        # Create expected signature using base64 encoding (Svix standard)
        import base64
        expected_signature = base64.b64encode(
            hmac.new(
                base64.b64decode(secret_key.encode('utf-8')),
                signed_payload.encode('utf-8'),
                hashlib.sha256
            ).digest()
        ).decode('utf-8')
        
        logger.debug(f"Expected signature: v1,{expected_signature[:10]}...") # Only log first 10 chars
        
        # Extract the signature from the svix-signature header (format: v1,signature)
        if ',' in svix_signature:
            version, signature = svix_signature.split(',', 1)
            if version == 'v1':
                result = hmac.compare_digest(signature, expected_signature)
                logger.debug(f"Signature match: {result}")
                return result
        
        logger.error(f"Invalid signature format: {svix_signature}")
        return False
        
    except Exception as e:
        logger.error(f"Signature verification error: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return False


def contact_stats_api(request):
    """API endpoint to get contact statistics"""
    try:
        stats = {
            'total_contacts': Contact.objects.count(),
            'not_sent': Contact.objects.filter(email_status='not_sent').count(),
            'sent': Contact.objects.filter(email_status='sent').count(),
            'delivered': Contact.objects.filter(email_status='delivered').count(),
            'opened': Contact.objects.filter(email_status='opened').count(),
            'clicked': Contact.objects.filter(email_status='clicked').count(),
            'bounced': Contact.objects.filter(email_status='bounced').count(),
            'complained': Contact.objects.filter(email_status='complained').count(),
            'failed': Contact.objects.filter(email_status='failed').count(),
        }
        return JsonResponse(stats)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def contacts_api(request):
    """API endpoint to get contacts list for custom selection"""
    try:
        # Get all contacts with essential fields for selection interface
        contacts = Contact.objects.all().values(
            'id', 'first_name', 'last_name', 'email', 'email_status',
            'company_name', 'job_title', 'location_country'
        ).order_by('first_name', 'last_name')
        
        return JsonResponse({
            'contacts': list(contacts)
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def delete_contact(request, contact_id):
    """View to delete a contact"""
    if request.method == 'POST':
        contact = get_object_or_404(Contact, id=contact_id)
        contact_name = contact.full_name or contact.email
        try:
            contact.delete()
            return JsonResponse({
                'success': True,
                'message': f'Contact {contact_name} deleted successfully!'
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': f'Failed to delete contact: {str(e)}'
            }, status=500)
    
    return JsonResponse({
        'success': False,
        'error': 'Invalid request method'
    }, status=405)


@csrf_exempt
def upload_csv(request):
    """View to upload and preview CSV contacts before batch creation"""
    # Handle RequestDataTooBig exception first
    try:
        # This will trigger the exception if request body is too large
        _ = request.POST
        _ = request.FILES
    except RequestDataTooBig:
        if request.method == 'POST':
            return JsonResponse({
                'success': False,
                'error': 'File or request too large. Please reduce the CSV file size (recommended: under 50MB) or select fewer contacts.'
            }, status=413)
        else:
            context = {
                'form': CSVUploadForm(),
                'title': 'Upload CSV Contacts',
                'error': 'Request too large. Please try with a smaller CSV file.'
            }
            return render(request, 'email_monitor/upload_csv.html', context)
    
    try:
        form = CSVUploadForm()  # Initialize form first
        
        if request.method == 'POST':
            # Debug logging
            print(f"POST data keys: {list(request.POST.keys())}")
            print(f"FILES data keys: {list(request.FILES.keys())}")
            
            if 'preview_csv' in request.POST:
                print("Processing CSV preview...")
                # Handle CSV preview
                form = CSVUploadForm(request.POST, request.FILES)
                print(f"Form is valid: {form.is_valid()}")
                if not form.is_valid():
                    print(f"Form errors: {form.errors}")
                
                if form.is_valid():
                    try:
                        csv_file = request.FILES['csv_file']
                        
                        # Check file size
                        if csv_file.size > 10 * 1024 * 1024:  # 10MB limit
                            return JsonResponse({
                                'success': False,
                                'error': 'File too large. Please keep CSV files under 10MB.'
                            }, status=400)
                        
                        # Try different encodings
                        content = None
                        for encoding in ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252']:
                            try:
                                csv_file.seek(0)  # Reset file pointer
                                content = csv_file.read().decode(encoding)
                                break
                            except UnicodeDecodeError:
                                continue
                        
                        if content is None:
                            return JsonResponse({
                                'success': False,
                                'error': 'Unable to decode CSV file. Please ensure it\'s properly encoded.'
                            }, status=400)
                        
                        # Check if content is empty
                        if not content.strip():
                            return JsonResponse({
                                'success': False,
                                'error': 'CSV file appears to be empty.'
                            }, status=400)
                        
                        csv_reader = csv.DictReader(io.StringIO(content))
                        
                        # Check if CSV has required columns
                        required_columns = ['VerifiedEmail', 'prospect_first_name', 'prospect_last_name']
                        fieldnames = csv_reader.fieldnames or []
                        missing_columns = [col for col in required_columns if col not in fieldnames]
                        
                        if missing_columns:
                            return JsonResponse({
                                'success': False,
                                'error': f'Missing required columns: {", ".join(missing_columns)}. Available columns: {", ".join(fieldnames)}'
                            }, status=400)
                        
                        contacts_preview = []
                        errors = []
                        line_number = 1
                        
                        try:
                            for row in csv_reader:
                                line_number += 1
                                
                                try:
                                    # Get email from VerifiedEmail column
                                    email = row.get('VerifiedEmail', '').strip()
                                    
                                    if not email or email.lower() == 'empty':
                                        errors.append(f"Line {line_number}: Missing or invalid email")
                                        continue
                                    
                                    # Basic email validation
                                    if '@' not in email or '.' not in email.split('@')[-1]:
                                        errors.append(f"Line {line_number}: Invalid email format: {email}")
                                        continue
                                    
                                    # Get basic info
                                    first_name = row.get('prospect_first_name', '').strip()
                                    last_name = row.get('prospect_last_name', '').strip()
                                    
                                    if not first_name or not last_name:
                                        errors.append(f"Line {line_number}: Missing first name or last name")
                                        continue
                                    
                                    # Check if contact already exists
                                    existing_contact = Contact.objects.filter(email=email).first()
                                    status = "Update" if existing_contact else "Create"
                                    
                                    # Handle location data - support both separate city/country fields and combined prospect_location
                                    location_city = row.get('prospect_location_city', '').strip()
                                    location_country = row.get('prospect_location_country', '').strip()
                                    
                                    # If separate fields are empty, try to parse prospect_location
                                    if not location_city and not location_country:
                                        prospect_location = row.get('prospect_location', '').strip()
                                        if prospect_location and prospect_location.lower() != 'empty':
                                            # Split by comma and clean up
                                            location_parts = [part.strip() for part in prospect_location.split(',')]
                                            location_parts = [part for part in location_parts if part and part.lower() != 'empty']
                                            
                                            if len(location_parts) >= 2:
                                                # Last part is usually country, first part(s) are city
                                                location_country = location_parts[-1]
                                                location_city = ', '.join(location_parts[:-1])
                                            elif len(location_parts) == 1:
                                                # Single location could be city or country
                                                single_location = location_parts[0]
                                                
                                                # Common country patterns - if it matches, put in country field
                                                country_patterns = [
                                                    'poland', 'germany', 'france', 'spain', 'italy', 'netherlands', 'belgium',
                                                    'uk', 'united kingdom', 'usa', 'united states', 'canada', 'australia',
                                                    'sweden', 'norway', 'denmark', 'finland', 'austria', 'switzerland',
                                                    'czech republic', 'slovakia', 'hungary', 'romania', 'bulgaria',
                                                    'portugal', 'ireland', 'greece', 'croatia', 'slovenia', 'estonia',
                                                    'latvia', 'lithuania', 'luxembourg', 'malta', 'cyprus'
                                                ]
                                                
                                                # Check if it looks like a country
                                                if any(country in single_location.lower() for country in country_patterns):
                                                    location_country = single_location
                                                else:
                                                    # Otherwise assume it's a city
                                                    location_city = single_location
                                    
                                    # Clean up location data - remove 'empty' values and normalize
                                    if location_city and location_city.lower() in ['empty', 'null', 'none', '']:
                                        location_city = ''
                                    if location_country and location_country.lower() in ['empty', 'null', 'none', '']:
                                        location_country = ''
                                    
                                    # Prepare contact data
                                    contact_data = {
                                        'email': email,
                                        'first_name': first_name,
                                        'last_name': last_name,
                                        'job_title': row.get('job_title', '').strip(),
                                        'company_name': row.get('company_name', '').strip(),
                                        'location_city': location_city,
                                        'location_country': location_country,
                                        'status': status,
                                        'existing_id': existing_contact.id if existing_contact else None,
                                        # Store all CSV data for batch creation
                                        'csv_data': {
                                            'location_city': location_city,
                                            'location_country': location_country,
                                            'prospect_location': row.get('prospect_location', '').strip(),  # Keep original for reference
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
                                    }
                                    
                                    contacts_preview.append(contact_data)
                                    
                                except Exception as row_error:
                                    errors.append(f"Line {line_number}: Error processing row - {str(row_error)}")
                                    continue
                        
                        except Exception as csv_error:
                            return JsonResponse({
                                'success': False,
                                'error': f'Error reading CSV data: {str(csv_error)}'
                            }, status=500)
                        
                        # Store preview data in session for batch creation
                        request.session['csv_contacts_preview'] = contacts_preview
                        
                        return JsonResponse({
                            'success': True,
                            'contacts': contacts_preview,
                            'errors': errors,
                            'total_contacts': len(contacts_preview),
                            'create_count': len([c for c in contacts_preview if c['status'] == 'Create']),
                            'update_count': len([c for c in contacts_preview if c['status'] == 'Update'])
                        })
                        
                    except Exception as e:
                        return JsonResponse({
                            'success': False,
                            'error': f'Error processing CSV: {str(e)}'
                        }, status=500)
                else:
                    errors = {}
                    for field, error_list in form.errors.items():
                        errors[field] = error_list[0]
                    
                    return JsonResponse({
                        'success': False,
                        'errors': errors
                    }, status=400)
            
            elif 'create_batch' in request.POST:
                # Handle batch creation
                try:
                    # Get selected contacts data from the request
                    selected_contacts_json = request.POST.get('selected_contacts')
                    if selected_contacts_json:
                        import json
                        try:
                            contacts_data = json.loads(selected_contacts_json)
                            print(f"DEBUG: Processing {len(contacts_data)} selected contacts")
                        except json.JSONDecodeError:
                            print("DEBUG: Failed to parse selected contacts JSON")
                            return JsonResponse({'success': False, 'error': 'Invalid selected contacts data'})
                    else:
                        # Fallback to session data if no selection (for backwards compatibility)
                        contacts_data = request.session.get('csv_contacts_preview', [])
                        print(f"DEBUG: No selection data, using session data with {len(contacts_data)} contacts")
                    
                    if not contacts_data:
                        return JsonResponse({
                            'success': False,
                            'error': 'No contacts to create. Please upload a CSV first.'
                        }, status=400)
                    
                    created_count = 0
                    updated_count = 0
                    errors = []
                    
                    for contact_data in contacts_data:
                        try:
                            # Get email and field values (either from modified form data or original data)
                            email = contact_data.get('email', '').strip()
                            first_name = contact_data.get('first_name', '').strip()
                            last_name = contact_data.get('last_name', '').strip()
                            company_name = contact_data.get('company_name', '').strip()
                            job_title = contact_data.get('job_title', '').strip()
                            location_city = contact_data.get('location_city', '').strip()
                            location_country = contact_data.get('location_country', '').strip()
                            
                            print(f"DEBUG: Processing contact: {email}")
                            
                            if not email:
                                continue
                            
                            # Create or update contact
                            contact, created = Contact.objects.get_or_create(
                                email=email,
                                defaults={
                                    'first_name': first_name,
                                    'last_name': last_name,
                                    'company_name': company_name,
                                    'job_title': job_title,
                                    'location_city': location_city,
                                    'location_country': location_country,
                                    'email_status': 'not_sent'
                                }
                            )
                            
                            if created:
                                created_count += 1
                                print(f"DEBUG: Created new contact: {email}")
                            else:
                                # Update existing contact with new data (only if fields have values)
                                updated = False
                                if first_name and contact.first_name != first_name:
                                    contact.first_name = first_name
                                    updated = True
                                if last_name and contact.last_name != last_name:
                                    contact.last_name = last_name
                                    updated = True
                                if company_name and contact.company_name != company_name:
                                    contact.company_name = company_name
                                    updated = True
                                if job_title and contact.job_title != job_title:
                                    contact.job_title = job_title
                                    updated = True
                                if location_city and contact.location_city != location_city:
                                    contact.location_city = location_city
                                    updated = True
                                if location_country and contact.location_country != location_country:
                                    contact.location_country = location_country
                                    updated = True
                                
                                if updated:
                                    contact.save()
                                    updated_count += 1
                                    print(f"DEBUG: Updated existing contact: {email}")
                        
                        except Exception as e:
                            error_msg = f"Error with {contact_data.get('email', 'unknown')}: {str(e)}"
                            errors.append(error_msg)
                            print(f"DEBUG: {error_msg}")
                    
                    # Clear session data
                    if 'csv_contacts_preview' in request.session:
                        del request.session['csv_contacts_preview']
                    
                    # Prepare response message
                    message_parts = []
                    if created_count > 0:
                        message_parts.append(f"Created {created_count} new contacts")
                    if updated_count > 0:
                        message_parts.append(f"Updated {updated_count} existing contacts")
                    
                    if not message_parts:
                        message_parts.append("No contacts were processed")
                    
                    message = ". ".join(message_parts) + "."
                    
                    return JsonResponse({
                        'success': True,
                        'message': message,
                        'created_count': created_count,
                        'updated_count': updated_count,
                        'errors': errors,
                        'redirect_url': '/monitor/contacts/'
                    })
                    
                except Exception as e:
                    return JsonResponse({
                        'success': False,
                        'error': f'Error creating contacts: {str(e)}'
                    }, status=500)
            else:
                # Debug: log when neither preview_csv nor create_batch is found
                print(f"No recognized action in POST data. Available keys: {list(request.POST.keys())}")
                return JsonResponse({
                    'success': False,
                    'error': 'No valid action specified in request'
                }, status=400)
        
        # If we reach here, it's either GET or POST without valid actions
        context = {
            'form': form,
            'title': 'Upload CSV Contacts'
        }
        return render(request, 'email_monitor/upload_csv.html', context)
    
    except Exception as e:
        # Catch any unhandled exceptions and return appropriate response
        if request.method == 'POST':
            return JsonResponse({
                'success': False,
                'error': f'Unexpected error: {str(e)}'
            }, status=500)
        else:
            # For GET requests, show error in template
            context = {
                'form': CSVUploadForm(),
                'title': 'Upload CSV Contacts',
                'error': f'Error: {str(e)}'
            }
            return render(request, 'email_monitor/upload_csv.html', context)


@csrf_exempt
def update_contact_field_api(request):
    """API endpoint to update a single contact field inline"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        contact_id = data.get('contact_id')
        field = data.get('field')
        value = data.get('value', '').strip()
        
        if not contact_id or not field:
            return JsonResponse({'success': False, 'error': 'Missing required fields'}, status=400)
        
        # Get the contact
        contact = get_object_or_404(Contact, id=contact_id)
        
        # Handle full_name specially - it's a computed property
        if field == 'full_name':
            # Split full name into first and last name
            name_parts = value.split(' ', 1) if value else ['', '']
            contact.first_name = name_parts[0]
            contact.last_name = name_parts[1] if len(name_parts) > 1 else ''
            contact.save()
            
            return JsonResponse({
                'success': True,
                'message': 'Name updated successfully'
            })
        
        # Map frontend field names to model field names
        field_mapping = {
            'first_name': 'first_name',
            'last_name': 'last_name',
            'job_title': 'job_title',
            'email': 'email',
            'company_name': 'company_name',
            'location_city': 'location_city',
            'location_country': 'location_country',
            'company_industry': 'company_industry',
            'linkedin_url': 'linkedin_url',
            'phone_number': 'phone_number',
            'leadscore': 'leadscore'
        }
        
        model_field = field_mapping.get(field)
        if not model_field:
            return JsonResponse({'success': False, 'error': 'Invalid field'}, status=400)
        
        # Validate specific fields
        if field == 'email' and value:
            from django.core.validators import validate_email
            from django.core.exceptions import ValidationError
            try:
                validate_email(value)
            except ValidationError:
                return JsonResponse({'success': False, 'error': 'Invalid email format'}, status=400)
            
            # Check for duplicate email
            if Contact.objects.exclude(id=contact_id).filter(email=value).exists():
                return JsonResponse({'success': False, 'error': 'Email already exists'}, status=400)
        
        if field == 'leadscore' and value:
            if value not in ['1', '2', '3']:
                return JsonResponse({'success': False, 'error': 'Lead score must be 1, 2, or 3'}, status=400)
        
        # Update the field
        setattr(contact, model_field, value if value else None)
        contact.save()
        
        return JsonResponse({
            'success': True,
            'message': f'{field.replace("_", " ").title()} updated successfully'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@csrf_exempt
def update_contact_batch_api(request):
    """API endpoint to update multiple contact fields at once"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        contact_id = data.get('contact_id')
        updates = data.get('updates', {})
        
        if not contact_id or not updates:
            return JsonResponse({'success': False, 'error': 'Missing required fields'}, status=400)
        
        # Get the contact
        contact = get_object_or_404(Contact, id=contact_id)
        
        # Handle full_name specially if present
        if 'full_name' in updates:
            full_name_value = updates.pop('full_name').strip() if updates.get('full_name') else ''
            name_parts = full_name_value.split(' ', 1) if full_name_value else ['', '']
            contact.first_name = name_parts[0]
            contact.last_name = name_parts[1] if len(name_parts) > 1 else ''
        
        # Map frontend field names to model field names
        field_mapping = {
            'first_name': 'first_name',
            'last_name': 'last_name',
            'job_title': 'job_title',
            'email': 'email',
            'company_name': 'company_name',
            'location_city': 'location_city',
            'location_country': 'location_country',
            'company_industry': 'company_industry',
            'linkedin_url': 'linkedin_url',
            'phone_number': 'phone_number',
            'leadscore': 'leadscore'
        }
        
        updated_fields = []
        
        # Track if full_name was updated
        if 'full_name' in updates:
            updated_fields.append('Full Name')
        
        # Process each update
        for field, value in updates.items():
            value = value.strip() if value else ''
            model_field = field_mapping.get(field)
            
            if not model_field:
                continue  # Skip invalid fields
            
            # Validate specific fields
            if field == 'email' and value:
                from django.core.validators import validate_email
                from django.core.exceptions import ValidationError
                try:
                    validate_email(value)
                except ValidationError:
                    return JsonResponse({'success': False, 'error': f'Invalid email format: {value}'}, status=400)
                
                # Check for duplicate email
                if Contact.objects.exclude(id=contact_id).filter(email=value).exists():
                    return JsonResponse({'success': False, 'error': f'Email already exists: {value}'}, status=400)
            
            if field == 'leadscore' and value:
                if value not in ['1', '2', '3']:
                    return JsonResponse({'success': False, 'error': 'Lead score must be 1, 2, or 3'}, status=400)
            
            # Update the field
            current_value = getattr(contact, model_field, '')
            if current_value != value:
                setattr(contact, model_field, value if value else None)
                updated_fields.append(field.replace('_', ' ').title())
        
        # Save all changes at once
        if updated_fields:
            contact.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Updated {len(updated_fields)} fields: {", ".join(updated_fields)}' if updated_fields else 'No changes made',
            'updated_fields': updated_fields
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@require_http_methods(["POST"])
def reset_database_api(request):
    """Reset database data - clears all contacts and email events"""
    try:
        # Parse the confirmation data
        data = json.loads(request.body)
        confirmation_text = data.get('confirmation', '').strip()
        
        # Require exact confirmation text for safety
        required_confirmation = "RESET DATABASE"
        if confirmation_text != required_confirmation:
            return JsonResponse({
                'success': False, 
                'error': f'Please type "{required_confirmation}" to confirm database reset'
            }, status=400)
        
        # Count records before deletion
        contacts_count = Contact.objects.count()
        events_count = EmailEvent.objects.count()
        
        # Delete all data
        Contact.objects.all().delete()
        EmailEvent.objects.all().delete()
        
        logger.info(f"Database reset completed - Deleted {contacts_count} contacts and {events_count} email events")
        
        return JsonResponse({
            'success': True,
            'message': f'Database reset successful! Deleted {contacts_count} contacts and {events_count} email events.',
            'deleted_contacts': contacts_count,
            'deleted_events': events_count
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.error(f"Database reset error: {str(e)}")
        return JsonResponse({'success': False, 'error': f'Database reset failed: {str(e)}'}, status=500)
