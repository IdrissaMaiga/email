from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
import json
from django.utils.decorators import method_decorator
from django.conf import settings
from django.utils import timezone
from django.db.models import Count, Q, Max
from django.db import models
from django.core.paginator import Paginator
from django.contrib import messages
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.core.exceptions import RequestDataTooBig
from .models import EmailEvent, EmailCampaign, Contact, EmailSender
from .forms import ContactForm, ContactSearchForm, CSVUploadForm
import json
import csv
import io
import hashlib
import hmac
import logging
import requests
import os
import base64
import traceback
import requests
import os
import base64
import traceback

logger = logging.getLogger(__name__)


def extract_email_from_sender_string(sender_string):
    """Extract email address from sender string like 'Name <email@domain.com>' or just 'email@domain.com'"""
    import re
    if not sender_string:
        return None
    
    # Try to extract email from "Name <email@domain.com>" format
    email_match = re.search(r'<([^>]+)>', sender_string)
    if email_match:
        return email_match.group(1).strip()
    
    # If no brackets found, assume the whole string is the email (after stripping whitespace)
    email = sender_string.strip()
    
    # Basic email validation
    if '@' in email and '.' in email:
        return email
    
    return None


def get_sender_from_email(email):
    """Get sender key from email address"""
    try:
        from .models import EmailSender
        
        # Get from database
        try:
            sender = EmailSender.objects.get(email=email, is_active=True)
            return sender.key
        except EmailSender.DoesNotExist:
            logger.warning(f"No active sender found for email: {email}")
            return None
        
    except Exception as e:
        logger.error(f"Error getting sender from email {email}: {str(e)}")
        return None


def get_sender_email(sender_key):
    """Get sender email from database"""
    try:
        from .models import EmailSender
        
        # Get from database
        try:
            sender = EmailSender.objects.get(key=sender_key, is_active=True)
            return sender.email
        except EmailSender.DoesNotExist:
            # No fallback, return None if not found
            logger.warning(f"No active sender found for key: {sender_key}")
            return None
        
    except Exception as e:
        logger.error(f"Error getting sender email for {sender_key}: {str(e)}")
        return None


def get_sender_email_map():
    """Get a mapping of sender keys to emails from database"""
    try:
        from .models import EmailSender
        
        # Get from database only
        db_senders = EmailSender.objects.filter(is_active=True)
        return {sender.key: sender.email for sender in db_senders}
        
    except Exception as e:
        logger.error(f"Error getting sender email map: {str(e)}")
        return {}


def contacts_list(request):
    """View to display all contacts from CSV with their email status"""
    
    # Get sender parameter to filter email events by sender
    sender = request.GET.get('sender')
    if not sender:
        # Check if there are any active senders at all
        from .models import EmailSender
        active_senders = EmailSender.objects.filter(is_active=True)
        
        if not active_senders.exists():
            # No senders configured, show setup message
            context = {
                'contacts': [],
                'stats': {
                    'total': 0,
                    'not_sent': 0,
                    'sent': 0,
                    'delivered': 0,
                    'opened': 0,
                    'clicked': 0,
                    'bounced': 0,
                    'failed': 0
                },
                'current_sender': None,
                'sender_email': None,
                'no_senders_configured': True,
                'message': 'No email senders configured. Please add email senders first.'
            }
            return render(request, 'email_monitor/contacts_list.html', context)
        else:
            # Use the first active sender as fallback and redirect with sender parameter
            first_sender = active_senders.first()
            from django.shortcuts import redirect
            from django.http import QueryDict
            
            # Preserve existing URL parameters
            query_params = request.GET.copy()
            query_params['sender'] = first_sender.key
            query_string = query_params.urlencode()
            
            return redirect(f"{request.path}?{query_string}")
        
    sender_email = get_sender_email(sender)
    
    # If no sender email found, return error or redirect to setup
    if not sender_email:
        # Check if there are any active senders at all
        from .models import EmailSender
        active_senders = EmailSender.objects.filter(is_active=True)
        
        if not active_senders.exists():
            # No senders configured, show setup message
            context = {
                'contacts': [],
                'stats': {
                    'total': 0,
                    'not_sent': 0,
                    'sent': 0,
                    'delivered': 0,
                    'opened': 0,
                    'clicked': 0,
                    'bounced': 0,
                    'failed': 0
                },
                'current_sender': sender,
                'sender_email': None,
                'no_senders_configured': True,
                'message': 'No email senders configured. Please add email senders first.'
            }
            return render(request, 'email_monitor/contacts_list.html', context)
        else:
            # Use the first active sender as fallback
            first_sender = active_senders.first()
            sender = first_sender.key
            sender_email = first_sender.email
    
    # Import needed Django query tools
    from django.db.models import OuterRef, Subquery, Case, When, Value, CharField
    
    # Subquery to get the most recent email event for each contact FROM THIS SENDER
    latest_event_subquery = EmailEvent.objects.filter(
        to_email=OuterRef('email'),
        from_email__icontains=sender_email  # Use icontains to match sender format like "Name <email@domain.com>"
    ).order_by('-created_at').values('event_type')[:1]
    
    # Subquery to get the latest event timestamp for activity tracking
    latest_event_time_subquery = EmailEvent.objects.filter(
        to_email=OuterRef('email'),
        from_email__icontains=sender_email
    ).order_by('-created_at').values('created_at')[:1]
    
    # Base queryset with annotations for email status
    contacts = Contact.objects.annotate(
        latest_event_type=Subquery(latest_event_subquery),
        last_email_sent=Subquery(latest_event_time_subquery),
        # Map event types to display status
        email_status=Case(
            When(latest_event_type='email.clicked', then=Value('clicked')),
            When(latest_event_type='email.opened', then=Value('opened')),
            When(latest_event_type='email.delivered', then=Value('delivered')),
            When(latest_event_type='email.sent', then=Value('sent')),
            When(latest_event_type='email.bounced', then=Value('bounced')),
            When(latest_event_type='email.complained', then=Value('complained')),
            When(latest_event_type='email.failed', then=Value('failed')),
            default=Value('not_sent'),
            output_field=CharField()
        ),
        # Human-readable display status
        display_status=Case(
            When(latest_event_type='email.clicked', then=Value('Clicked')),
            When(latest_event_type='email.opened', then=Value('Opened')),
            When(latest_event_type='email.delivered', then=Value('Delivered')),
            When(latest_event_type='email.sent', then=Value('Sent')),
            When(latest_event_type='email.bounced', then=Value('Bounced')),
            When(latest_event_type='email.complained', then=Value('Complained')),
            When(latest_event_type='email.failed', then=Value('Failed')),
            default=Value('Not Sent'),
            output_field=CharField()
        )
    )
    
    # Add activity tracking annotations
    contacts = contacts.annotate(
        last_opened=Subquery(
            EmailEvent.objects.filter(
                to_email=OuterRef('email'),
                from_email__icontains=sender_email,
                event_type='email.opened'
            ).order_by('-created_at').values('created_at')[:1]
        ),
        last_clicked=Subquery(
            EmailEvent.objects.filter(
                to_email=OuterRef('email'),
                from_email__icontains=sender_email,
                event_type='email.clicked'
            ).order_by('-created_at').values('created_at')[:1]
        )
    )
    
    # Filter by status if specified
    status_filter = request.GET.get('status')
    if status_filter and status_filter != 'all':
        if status_filter == 'not_sent':
            # Show contacts with no email events from this sender
            contacts = contacts.filter(latest_event_type__isnull=True)
        else:
            # Map status filter to event type
            event_type_map = {
                'sent': 'email.sent',
                'delivered': 'email.delivered', 
                'opened': 'email.opened',
                'clicked': 'email.clicked',
                'bounced': 'email.bounced',
                'complained': 'email.complained',
                'failed': 'email.failed'
            }
            target_event_type = event_type_map.get(status_filter)
            if target_event_type:
                contacts = contacts.filter(latest_event_type=target_event_type)
    
    # Filter by category if specified
    category_filter = request.GET.get('category')
    if category_filter and category_filter != 'all':
        contacts = contacts.filter(category_id=category_filter)
    
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
    
    # Get status counts for the filter buttons based on actual email events FROM THIS SENDER
    from django.db.models import OuterRef, Subquery, Count, Case, When, Value, CharField
    
    # Subquery to get the most recent email event for each contact FROM THIS SENDER
    latest_event_subquery = EmailEvent.objects.filter(
        to_email=OuterRef('email'),
        from_email__icontains=sender_email  # Use icontains to match sender format like "Name <email@domain.com>"
    ).order_by('-created_at').values('event_type')[:1]
    
    # Annotate all contacts with their latest event type from this sender
    contacts_with_events = Contact.objects.annotate(
        latest_event_type=Subquery(latest_event_subquery)
    )
    
    # Count contacts by their latest email event status from this sender
    status_counts = {}
    status_counts['not_sent'] = contacts_with_events.filter(latest_event_type__isnull=True).count()
    status_counts['sent'] = contacts_with_events.filter(latest_event_type='email.sent').count()
    status_counts['delivered'] = contacts_with_events.filter(latest_event_type='email.delivered').count()
    status_counts['opened'] = contacts_with_events.filter(latest_event_type='email.opened').count()
    status_counts['clicked'] = contacts_with_events.filter(latest_event_type='email.clicked').count()
    status_counts['bounced'] = contacts_with_events.filter(latest_event_type='email.bounced').count()
    status_counts['complained'] = contacts_with_events.filter(latest_event_type='email.complained').count()
    status_counts['failed'] = contacts_with_events.filter(latest_event_type='email.failed').count()
    
    # Status choices for the filter buttons
    status_choices = [
        ('not_sent', 'Not Sent'),
        ('sent', 'Sent'),
        ('delivered', 'Delivered'),
        ('opened', 'Opened'),
        ('clicked', 'Clicked'),
        ('bounced', 'Bounced'),
        ('complained', 'Complained'),
        ('failed', 'Failed'),
    ]
    
    # Get all distinct categories for filtering with counts
    categories = []
    distinct_categories = Contact.objects.values('category_id', 'category_name').distinct().order_by('category_id')
    for category in distinct_categories:
        cat_id = category['category_id']
        count = Contact.objects.filter(category_id=cat_id).count()
        categories.append({
            'category_id': cat_id,
            'category_name': category['category_name'],
            'count': count
        })
    
    context = {
        'page_obj': page_obj,
        'status_counts': status_counts,
        'status_choices': status_choices,
        'categories': categories,
        'current_status': status_filter,
        'current_search': search,
        'current_sort': sort_by,
        'current_category': category_filter,
    }
    
    return render(request, 'email_monitor/contacts_list.html', context)


def contact_email_content_api(request):
    """API endpoint to get email content for a specific contact"""
    email = request.GET.get('email')
    if not email:
        return JsonResponse({'error': 'Email parameter is required'}, status=400)
    
    try:
        # Get sender parameter to determine which sender's emails to show
        sender = request.GET.get('sender')
        if not sender:
            return JsonResponse({'error': 'Sender parameter is required'}, status=400)
            
        sender_email = get_sender_email(sender)
        
        # If no sender email found, return error
        if not sender_email:
            return JsonResponse({'error': f'Sender "{sender}" not found or not active'}, status=400)
        
        # Import needed Django query tools
        from django.db.models import OuterRef, Subquery, Case, When, Value, CharField
        
        # Subquery to get the most recent email event for this contact FROM THIS SENDER
        latest_event_subquery = EmailEvent.objects.filter(
            to_email=OuterRef('email'),
            from_email__icontains=sender_email
        ).order_by('-created_at').values('event_type')[:1]
        
        # Get the contact with proper annotations
        contact = Contact.objects.annotate(
            latest_event_type=Subquery(latest_event_subquery),
            # Human-readable display status
            display_status=Case(
                When(latest_event_type='email.clicked', then=Value('Clicked')),
                When(latest_event_type='email.opened', then=Value('Opened')),
                When(latest_event_type='email.delivered', then=Value('Delivered')),
                When(latest_event_type='email.sent', then=Value('Sent')),
                When(latest_event_type='email.bounced', then=Value('Bounced')),
                When(latest_event_type='email.complained', then=Value('Complained')),
                When(latest_event_type='email.failed', then=Value('Failed')),
                default=Value('Not Sent'),
                output_field=CharField()
            )
        ).filter(email=email).first()
        
        if not contact:
            return JsonResponse({'error': 'Contact not found'}, status=404)
        
        # Find the last 3 email events for this contact FROM THIS SENDER (all event types)
        recent_events = EmailEvent.objects.filter(
            to_email=email,
            from_email__icontains=sender_email
        ).order_by('-created_at')[:3]
        
        if not recent_events:
            return JsonResponse({'error': 'No email events found for this contact from this sender'}, status=404)
        
        # Get the most recent event for the main email content (prioritize events with email_id)
        most_recent_event = None
        for event in recent_events:
            if event.email_id:  # Prioritize events that have email content
                most_recent_event = event
                break
        
        # If no event has email_id, use the most recent one anyway
        if not most_recent_event:
            most_recent_event = recent_events[0]
        email_id = most_recent_event.email_id
        if not email_id:
            # If no email_id, we can still show the events history without email content
            response_data = {
                'to_email': email,
                'subject': 'No email content available',
                'sent_date': most_recent_event.created_at.isoformat(),
                'status': contact.display_status,
                'html_content': None,
                'text_content': None,
                'event_type': most_recent_event.event_type,
                'email_id': None,
                'recent_events': [
                    {
                        'event_type': event.event_type,
                        'created_at': event.created_at.isoformat(),
                        'email_id': event.email_id,
                        'event_id': event.event_id,
                        'to_email': event.to_email,
                        'click_url': getattr(event, 'click_url', None),
                        'bounce_reason': getattr(event, 'bounce_reason', None),
                        'complaint_feedback_type': getattr(event, 'complaint_feedback_type', None)
                    } for event in recent_events
                ]
            }
            return JsonResponse(response_data)
        
        # Fetch email content from Resend API
        import requests
        import os
        
        # Determine which API key to use based on the sender
        # First try to get the sender from the recent event
        from_email_raw = most_recent_event.from_email if most_recent_event.from_email else ''
        
        # Extract just the email address from the sender string
        from_email = extract_email_from_sender_string(from_email_raw)
        
        # Get the appropriate API key from database
        resend_api_key = None
        sender_obj = None
        
        if from_email:
            try:
                sender_obj = EmailSender.objects.get(email=from_email, is_active=True)
                resend_api_key = sender_obj.api_key
            except EmailSender.DoesNotExist:
                pass
        
        if not resend_api_key:
            return JsonResponse({'error': f'Resend API key not configured for sender: {from_email}'}, status=500)
        
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
                'event_type': most_recent_event.event_type,
                'email_id': email_id,
                'recent_events': [
                    {
                        'event_type': event.event_type,
                        'created_at': event.created_at.isoformat(),
                        'email_id': event.email_id,
                        'event_id': event.event_id,
                        'to_email': event.to_email,
                        'click_url': getattr(event, 'click_url', None),
                        'bounce_reason': getattr(event, 'bounce_reason', None),
                        'complaint_feedback_type': getattr(event, 'complaint_feedback_type', None)
                    } for event in recent_events
                ]
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


def email_content_by_id_api(request):
    """API endpoint to get email content by email_id directly"""
    email_id = request.GET.get('email_id')
    if not email_id:
        return JsonResponse({'error': 'Email ID parameter is required'}, status=400)
    
    try:
        # Get sender parameter to determine which API key to use
        sender = request.GET.get('sender')
        if not sender:
            return JsonResponse({'error': 'Sender parameter is required'}, status=400)
            
        sender_email = get_sender_email(sender)
        
        # If no sender email found, return error
        if not sender_email:
            return JsonResponse({'error': f'Sender "{sender}" not found or not active'}, status=400)
        
        # Find the email event with this email_id
        email_event = EmailEvent.objects.filter(
            email_id=email_id,
            from_email__icontains=sender_email
        ).first()
        
        if not email_event:
            return JsonResponse({'error': 'Email event not found for this sender'}, status=404)
        
        # Get API key from database
        resend_api_key = None
        if email_event.from_email:
            # Extract email address from sender string
            from_email = extract_email_from_sender_string(email_event.from_email)
            
            try:
                sender_obj = EmailSender.objects.get(email=from_email, is_active=True)
                resend_api_key = sender_obj.api_key
            except EmailSender.DoesNotExist:
                pass
                
        # Fallback to any active sender if no specific match
        if not resend_api_key:
            try:
                fallback_sender = EmailSender.objects.filter(is_active=True).first()
                if fallback_sender:
                    resend_api_key = fallback_sender.api_key
            except Exception as e:
                pass

        if not resend_api_key:
            return JsonResponse({'error': f'Resend API key not configured for sender: {from_email}'}, status=500)
        
        # Make request to Resend API to get email content
        headers = {
            'Authorization': f'Bearer {resend_api_key}',
            'Content-Type': 'application/json'
        }
        
        resend_url = f'https://api.resend.com/emails/{email_id}'
        response = requests.get(resend_url, headers=headers)
        
        if response.status_code == 200:
            email_data = response.json()
            
            response_data = {
                'subject': email_data.get('subject') or 'No subject',
                'sent_date': email_data.get('created_at'),
                'html_content': email_data.get('html'),
                'text_content': email_data.get('text'),
                'email_id': email_id,
                'event_type': email_event.event_type
            }
            
            return JsonResponse(response_data)
        else:
            return JsonResponse({
                'error': f'Failed to fetch email from Resend API: {response.status_code} - {response.text}'
            }, status=500)
        
    except Exception as e:
        return JsonResponse({'error': f'Failed to retrieve email content: {str(e)}'}, status=500)


def webhook_handler_view(request, endpoint):
    """
    Generic webhook endpoint that determines sender from webhook URL path
    URL: sender.horizoneurope.io/webhook/<endpoint>/
    """
    from .models import EmailSender
    
    # Find sender where webhook_url ends with '/<endpoint>/'
    try:
        sender = EmailSender.objects.get(
            webhook_url__endswith=f'/{endpoint}/',
            is_active=True
        )
        return webhook_handler(request, sender.key)
    except EmailSender.DoesNotExist:
        logger.error(f"No active sender found for webhook endpoint: {endpoint}")
        return HttpResponse("Invalid endpoint", status=400)
    except EmailSender.MultipleObjectsReturned:
        logger.error(f"Multiple senders found for webhook endpoint: {endpoint}")
        return HttpResponse("Ambiguous endpoint", status=400)

def webhook_handler(request, sender_key):
    """
    Common webhook handler for all sender configurations
    """
    try:
        # Get sender configuration from database
        try:
            from .models import EmailSender
            sender_obj = EmailSender.objects.get(key=sender_key, is_active=True)
            webhook_secret = sender_obj.webhook_secret
        except EmailSender.DoesNotExist:
            # Fallback to settings if not in database
            email_senders = getattr(settings, 'EMAIL_SENDERS', {})
            if sender_key not in email_senders:
                logger.error(f"Invalid sender key: {sender_key}")
                return HttpResponse("Invalid sender key", status=400)
            
            sender_config = email_senders[sender_key]
            webhook_secret = sender_config.get('webhook_secret')
        
        if not webhook_secret:
            logger.error(f"No webhook secret configured for sender: {sender_key}")
            return HttpResponse("No webhook secret configured", status=400)
        
        # Verify webhook signature
        if not verify_webhook_signature(request, webhook_secret):
            logger.error(f"Invalid webhook signature for sender: {sender_key}")
            return HttpResponse("Invalid signature", status=403)
        
        # Parse webhook payload
        raw_body = request.body.decode('utf-8')
        payload = json.loads(raw_body)
        
        # Log the full payload for debugging
        logger.info(f"✅ WEBHOOK: Received payload for {sender_key}: {payload}")
        print(f"✅ WEBHOOK: Received payload for {sender_key}: {payload}")
        
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
        
        print(f"✅ EMAIL EVENT: Created {event_type} event for {event_data.get('to_email')} with ID {event_id}")
        
        # Update contact status based on email event
        if event_data.get('to_email'):
            try:
                contact = Contact.objects.filter(email=event_data['to_email']).first()
                if contact:
                    print(f"✅ CONTACT: Found contact {contact.full_name} ({contact.email})")
                else:
                    print(f"⚠️ CONTACT: No contact found for email {event_data.get('to_email')}")
                
                # Note: We no longer update contact status since contacts are independent entities
                # Email status is tracked through EmailEvent objects, not on the contact itself
                # This allows one contact to have multiple email statuses from different senders
                
            except Exception as e:
                # Handle any other database issues
                print(f"❌ CONTACT ERROR: {str(e)} for email {event_data.get('to_email')}")
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
    """API endpoint to get contact statistics filtered by sender and optionally by category"""
    from django.db.models import Subquery, OuterRef
    
    try:
        # Get sender parameter from request
        sender = request.GET.get('sender')
        if not sender:
            return JsonResponse({'error': 'Sender parameter is required'}, status=400)
            
        category_filter = request.GET.get('category')  # Optional category filter
        
        # Map sender to email domain for filtering
        sender_email = get_sender_email(sender)
        
        # If no sender email found, return error
        if not sender_email:
            return JsonResponse({'error': f'Sender "{sender}" not found or not active'}, status=400)
        
        # Debug: Let's see what emails have been sent by each sender
        debug_mode = request.GET.get('debug', 'false').lower() == 'true'
        if debug_mode:
            # Get unique sender emails from EmailEvents
            email_events_senders = EmailEvent.objects.values_list('from_email', flat=True).distinct()
            sender_event_counts = {}
            for event_sender in email_events_senders:
                if event_sender:  # Skip None values
                    count = EmailEvent.objects.filter(from_email__icontains=event_sender).count()
                    sender_event_counts[event_sender] = count
            
            # Get contacts that have been emailed by this sender
            contacted_emails = EmailEvent.objects.filter(
                from_email__icontains=sender_email
            ).values_list('to_email', flat=True).distinct()
            
            return JsonResponse({
                'debug': True,
                'requested_sender': sender,
                'mapped_sender_email': sender_email,
                'email_events_by_sender': sender_event_counts,
                'contacts_emailed_by_sender': len(contacted_emails),
                'total_contacts_all': Contact.objects.count(),
                'total_email_events': EmailEvent.objects.count()
            })
        
        # Get ALL contacts (contacts are independent of senders)
        sender_contacts = Contact.objects.all()
        
        # Apply category filter if specified
        if category_filter:
            sender_contacts = sender_contacts.filter(category_id=category_filter)
        
        total_contacts = sender_contacts.count()
        
        # Count contacts by their LATEST email status using EmailEvent records
        # Note: EmailEvent.from_email may contain full sender format like "Name <email@domain.com>"
        # so we need to use icontains to match the email part
        
        from django.db.models import Subquery
        
        # Get the most recent email event for each contact from this sender
        latest_event_subquery = EmailEvent.objects.filter(
            to_email=OuterRef('email'),
            from_email__icontains=sender_email
        ).order_by('-created_at').values('event_type')[:1]
        
        # Annotate contacts with their latest event type from this sender
        contacts_with_latest_event = sender_contacts.annotate(
            latest_event_type=Subquery(latest_event_subquery)
        )
        
        # Count contacts based on their latest email event type
        not_sent_count = contacts_with_latest_event.filter(latest_event_type__isnull=True).count()
        sent_count = contacts_with_latest_event.filter(latest_event_type='email.sent').count()
        delivered_count = contacts_with_latest_event.filter(latest_event_type='email.delivered').count()
        opened_count = contacts_with_latest_event.filter(latest_event_type='email.opened').count()
        clicked_count = contacts_with_latest_event.filter(latest_event_type='email.clicked').count()
        bounced_count = contacts_with_latest_event.filter(latest_event_type='email.bounced').count()
        failed_count = contacts_with_latest_event.filter(latest_event_type='email.failed').count()
        complained_count = contacts_with_latest_event.filter(latest_event_type='email.complained').count()
        
        # Prepare category text for explanations
        category_text = f' in category "{category_filter}"' if category_filter else ''
        
        stats = {
            'total_contacts': total_contacts,
            'total_email_events': contacts_with_latest_event.exclude(latest_event_type__isnull=True).count(),
            'not_sent': not_sent_count,
            'sent': sent_count,
            'delivered': delivered_count,
            'opened': opened_count,
            'clicked': clicked_count,
            'bounced': bounced_count,
            'complained': complained_count,
            'failed': failed_count,
            'sender': sender,
            'sender_email': sender_email,
            'category_filter': category_filter,
            'stats_explanation': {
                'total_contacts': f'Total number of contact records{category_text} (shared across all senders)',
                'total_email_events': f'Number of contacts{category_text} with email events from this sender',
                'status_counts': f'Contact counts{category_text} based on their latest email status from this sender only'
            }
        }
        return JsonResponse(stats)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def contacts_api(request):
    """API endpoint to get contacts list for custom selection filtered by sender"""
    try:
        # Get sender parameter from request
        sender = request.GET.get('sender')
        if not sender:
            return JsonResponse({'error': 'Sender parameter is required'}, status=400)
        
        # Map sender to email domain for filtering
        sender_email = get_sender_email(sender)
        
        # If no sender email found, return error
        if not sender_email:
            return JsonResponse({'error': f'Sender "{sender}" not found or not active'}, status=400)
        
        # Import needed Django query tools
        from django.db.models import OuterRef, Subquery, Case, When, Value, CharField
        
        # Subquery to get the most recent email event for each contact FROM THIS SENDER
        latest_event_subquery = EmailEvent.objects.filter(
            to_email=OuterRef('email'),
            from_email__icontains=sender_email  # Use icontains to match sender format like "Name <email@domain.com>"
        ).order_by('-created_at').values('event_type')[:1]
        
        # Get contacts with email status annotations based on latest email events
        contacts = Contact.objects.annotate(
            latest_event_type=Subquery(latest_event_subquery),
            # Map event types to display status
            email_status=Case(
                When(latest_event_type='email.clicked', then=Value('clicked')),
                When(latest_event_type='email.opened', then=Value('opened')),
                When(latest_event_type='email.delivered', then=Value('delivered')),
                When(latest_event_type='email.sent', then=Value('sent')),
                When(latest_event_type='email.bounced', then=Value('bounced')),
                When(latest_event_type='email.complained', then=Value('complained')),
                When(latest_event_type='email.failed', then=Value('failed')),
                default=Value('not_sent'),
                output_field=CharField()
            )
        ).values(
            'id', 'first_name', 'last_name', 'email',
            'company_name', 'job_title', 'location_country', 'email_status'
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
            
            if 'preview_csv' in request.POST:
                # Handle CSV preview
                form = CSVUploadForm(request.POST, request.FILES)
                
                if form.is_valid():
                    # Get category information
                    category_choice = form.cleaned_data.get('category_choice')
                    existing_category = form.cleaned_data.get('existing_category')
                    new_category_name = form.cleaned_data.get('new_category_name')
                    
                    # Determine the final category name
                    if category_choice == 'existing':
                        final_category_name = existing_category
                    else:
                        final_category_name = new_category_name
                    
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
                                    # Debug: Check if row is None or empty
                                    if not row:
                                        errors.append(f"Line {line_number}: Empty row")
                                        continue
                                    
                                    # Get email from VerifiedEmail column with safe handling
                                    email = row.get('VerifiedEmail') or ''
                                    if email:
                                        email = email.strip()
                                    
                                    if not email or email.lower() == 'empty':
                                        errors.append(f"Line {line_number}: Missing or invalid email")
                                        continue
                                    
                                    # Basic email validation
                                    if '@' not in email or '.' not in email.split('@')[-1]:
                                        errors.append(f"Line {line_number}: Invalid email format: {email}")
                                        continue
                                    
                                    # Get basic info with safe handling
                                    first_name = row.get('prospect_first_name') or ''
                                    if first_name:
                                        first_name = first_name.strip()
                                    
                                    last_name = row.get('prospect_last_name') or ''
                                    if last_name:
                                        last_name = last_name.strip()
                                    
                                    if not first_name or not last_name:
                                        errors.append(f"Line {line_number}: Missing first name or last name")
                                        continue
                                    
                                    # Check if contact already exists
                                    existing_contact = Contact.objects.filter(email=email).first()
                                    status = "Update" if existing_contact else "Create"
                                    
                                    # Handle location data - support both separate city/country fields and combined prospect_location
                                    location_city = row.get('prospect_location_city') or ''
                                    if location_city:
                                        location_city = location_city.strip()
                                    
                                    location_country = row.get('prospect_location_country') or ''
                                    if location_country:
                                        location_country = location_country.strip()
                                    
                                    # If separate fields are empty, try to parse prospect_location
                                    if not location_city and not location_country:
                                        prospect_location = row.get('prospect_location') or ''
                                        if prospect_location:
                                            prospect_location = prospect_location.strip()
                                        
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
                                    
                                    # Safe field extraction
                                    def safe_get(field_name):
                                        value = row.get(field_name) or ''
                                        # Ensure value is a string before calling strip()
                                        value_str = str(value) if value is not None else ''
                                        return value_str.strip() if value_str else ''
                                    
                                    # Prepare contact data
                                    contact_data = {
                                        'email': email,
                                        'first_name': first_name,
                                        'last_name': last_name,
                                        'job_title': safe_get('job_title'),
                                        'company_name': safe_get('company_name'),
                                        'location_city': location_city,
                                        'location_country': location_country,
                                        'status': status,
                                        'existing_id': existing_contact.id if existing_contact else None,
                                        # Store all CSV data for batch creation
                                        'csv_data': {
                                            'location_city': location_city,
                                            'location_country': location_country,
                                            'prospect_location': safe_get('prospect_location'),  # Keep original for reference
                                            'company_name': safe_get('company_name'),
                                            'company_industry': safe_get('company_industry'),
                                            'company_website': safe_get('company_website'),
                                            'company_description': safe_get('company_description'),
                                            'company_linkedin_url': safe_get('company_linkedin_url'),
                                            'company_headcount': safe_get('company_headcount'),
                                            'job_title': safe_get('job_title'),
                                            'linkedin_url': safe_get('linkedin_url'),
                                            'linkedin_headline': safe_get('linkedin_headline'),
                                            'linkedin_position': safe_get('linkedin_position'),
                                            'linkedin_summary': safe_get('linkedin_summary'),
                                            'phone_number': safe_get('phone_number'),
                                            'tailored_tone_first_line': safe_get('tailored_tone_first_line'),
                                            'tailored_tone_ps_statement': safe_get('tailored_tone_ps_statement'),
                                            'tailored_tone_subject': safe_get('tailored_tone_subject'),
                                            'custom_ai_1': safe_get('custom_ai_1'),
                                            'custom_ai_2': safe_get('custom_ai_2'),
                                            'profile_image_url': safe_get('profile_image_url'),
                                            'logo_image_url': safe_get('logo_image_url'),
                                            'funnel_unique_id': safe_get('funnel_unique_id'),
                                            'funnel_step': safe_get('funnel_step'),
                                            'sequence_unique_id': safe_get('sequence_unique_id'),
                                            'variation_unique_id': safe_get('variation_unique_id'),
                                            'websitecontent': safe_get('websitecontent'),
                                            'leadscore': safe_get('leadscore'),
                                            'esp': safe_get('ESP'),
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
                        request.session['csv_category_info'] = {
                            'category_choice': category_choice,
                            'category_name': final_category_name
                        }
                        
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
                        except json.JSONDecodeError:
                            return JsonResponse({'success': False, 'error': 'Invalid selected contacts data'})
                    else:
                        # Fallback to session data if no selection (for backwards compatibility)
                        contacts_data = request.session.get('csv_contacts_preview', [])
                    
                    if not contacts_data:
                        return JsonResponse({
                            'success': False,
                            'error': 'No contacts to create. Please upload a CSV first.'
                        }, status=400)
                    
                    # Get category information from session
                    category_info = request.session.get('csv_category_info', {})
                    category_name = category_info.get('category_name', '')
                    
                    # If no category specified, create a default one
                    if not category_name:
                        from datetime import datetime
                        category_name = f"Import_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                    
                    # Check if this category already exists, if not, generate new category_id
                    existing_category = Contact.objects.filter(category_name=category_name).first()
                    if existing_category:
                        category_id = existing_category.category_id
                    else:
                        # Generate next available category_id
                        max_category_id = Contact.objects.aggregate(
                            max_id=models.Max('category_id')
                        )['max_id'] or 0
                        # Handle both string and integer category_id values
                        if isinstance(max_category_id, str):
                            try:
                                max_category_id = int(max_category_id)
                            except (ValueError, TypeError):
                                max_category_id = 0
                        category_id = str(max_category_id + 1)  # Keep as string for now
                    
                    created_count = 0
                    updated_count = 0
                    errors = []
                    
                    for contact_data in contacts_data:
                        try:
                            # Get email and field values (either from modified form data or original data)
                            # Ensure all values are converted to strings before calling strip()
                            email = str(contact_data.get('email', '')).strip()
                            first_name = str(contact_data.get('first_name', '')).strip()
                            last_name = str(contact_data.get('last_name', '')).strip()
                            company_name = str(contact_data.get('company_name', '')).strip()
                            job_title = str(contact_data.get('job_title', '')).strip()
                            location_city = str(contact_data.get('location_city', '')).strip()
                            location_country = str(contact_data.get('location_country', '')).strip()
                            
                            if not email:
                                continue
                            
                            # Check if contact with this email already exists in this category (use string comparison)
                            existing_contact = Contact.objects.filter(
                                email=email,
                                category_id=str(category_id)
                            ).first()
                            
                            if existing_contact:
                                # Update existing contact
                                updated = False
                                if first_name and existing_contact.first_name != first_name:
                                    existing_contact.first_name = first_name
                                    updated = True
                                if last_name and existing_contact.last_name != last_name:
                                    existing_contact.last_name = last_name
                                    updated = True
                                if company_name and existing_contact.company_name != company_name:
                                    existing_contact.company_name = company_name
                                    updated = True
                                if job_title and existing_contact.job_title != job_title:
                                    existing_contact.job_title = job_title
                                    updated = True
                                if location_city and existing_contact.location_city != location_city:
                                    existing_contact.location_city = location_city
                                    updated = True
                                if location_country and existing_contact.location_country != location_country:
                                    existing_contact.location_country = location_country
                                    updated = True
                                
                                if updated:
                                    existing_contact.save()
                                    updated_count += 1
                            else:
                                # Create new contact - find the next available contact_id within this category
                                used_contact_ids = set(
                                    Contact.objects.filter(category_id=str(category_id))
                                    .values_list('contact_id', flat=True)
                                )
                                
                                # Find the lowest unused contact_id for this category
                                contact_id = 1
                                while contact_id in used_contact_ids:
                                    contact_id += 1
                                
                                # Create the contact (keep category_id as string for now)
                                contact = Contact.objects.create(
                                    email=email,
                                    first_name=first_name,
                                    last_name=last_name,
                                    company_name=company_name,
                                    job_title=job_title,
                                    location_city=location_city,
                                    location_country=location_country,
                                    category_name=category_name,
                                    category_id=str(category_id),
                                    contact_id=contact_id
                                )
                                created_count += 1
                        
                        except Exception as e:
                            error_msg = f"Error with {contact_data.get('email', 'unknown')}: {str(e)}"
                            errors.append(error_msg)
                    
                    # Clear session data
                    if 'csv_contacts_preview' in request.session:
                        del request.session['csv_contacts_preview']
                    if 'csv_category_info' in request.session:
                        del request.session['csv_category_info']
                    
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
                # Return error for unrecognized actions
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
def add_contact_api(request):
    """API endpoint to add a new contact manually"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        
        # Required fields
        email = data.get('email', '').strip()
        first_name = data.get('first_name', '').strip()
        last_name = data.get('last_name', '').strip()
        category_name = data.get('category_name', 'Default Category').strip()
        
        if not email or not first_name or not last_name or not category_name:
            return JsonResponse({'success': False, 'error': 'Email, first name, last name, and category name are required'}, status=400)
        
        # Validate email format
        from django.core.validators import validate_email
        from django.core.exceptions import ValidationError
        try:
            validate_email(email)
        except ValidationError:
            return JsonResponse({'success': False, 'error': 'Invalid email format'}, status=400)
        
        # Check if this category already exists, if not, generate new category_id
        existing_category = Contact.objects.filter(category_name=category_name).first()
        if existing_category:
            category_id = existing_category.category_id
        else:
            # Generate next available category_id
            from django.db.models import Max
            max_category_id = Contact.objects.aggregate(max_id=Max('category_id'))['max_id'] or 0
            # Handle both string and integer category_id values
            if isinstance(max_category_id, str):
                try:
                    max_category_id = int(max_category_id)
                except (ValueError, TypeError):
                    max_category_id = 0
            category_id = str(max_category_id + 1)  # Keep as string for now
        
        # Check for duplicate email within the same category (use string comparison for now)
        if Contact.objects.filter(category_id=str(category_id), email=email).exists():
            return JsonResponse({'success': False, 'error': 'A contact with this email already exists in this category'}, status=400)
        
        # Optional fields
        job_title = data.get('job_title', '').strip()
        company_name = data.get('company_name', '').strip()
        location_city = data.get('location_city', '').strip()
        location_country = data.get('location_country', '').strip()
        linkedin_url = data.get('linkedin_url', '').strip()
        
        # Find the next contact_id for this category (use string comparison for now)
        from django.db.models import Max
        max_contact_id = Contact.objects.filter(category_id=str(category_id)).aggregate(
            max_id=Max('contact_id')
        )['max_id'] or 0
        next_contact_id = max_contact_id + 1
        
        # Create new contact
        contact = Contact(
            category_id=str(category_id),  # Keep as string for now
            category_name=category_name,
            contact_id=next_contact_id,
            email=email,
            first_name=first_name,
            last_name=last_name,
            job_title=job_title,
            company_name=company_name,
            location_city=location_city,
            location_country=location_country,
            linkedin_url=linkedin_url
        )
        contact.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Contact {contact.full_name} added successfully to {category_name}!',
            'category_id': contact.category_id,
            'contact_id': contact.contact_id
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': f'Failed to add contact: {str(e)}'}, status=500)


@csrf_exempt
def get_categories_api(request):
    """API endpoint to get all existing categories with count and ID"""
    if request.method != 'GET':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)
    
    try:
        # Get all unique categories with their IDs and contact counts
        categories_data = Contact.objects.values('category_id', 'category_name').annotate(
            contact_count=Count('id')
        ).exclude(
            category_name__isnull=True
        ).exclude(
            category_name=''
        ).order_by('category_name')
        
        # Convert to list and ensure all fields are present
        categories_list = []
        for category in categories_data:
            categories_list.append({
                'category_id': category['category_id'] or 'undefined',
                'category_name': category['category_name'] or 'undefined',
                'contact_count': category['contact_count']
            })
        
        return JsonResponse({
            'success': True,
            'categories': categories_list
        })
    except Exception as e:
        # Handle case where category fields don't exist yet (pre-migration)
        return JsonResponse({
            'success': False,
            'error': f'Categories not available yet: {str(e)}',
            'categories': []
        })


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


# Email Sender Management APIs

@csrf_exempt
def email_senders_api(request):
    """API to get all email senders"""
    if request.method == 'GET':
        try:
            from .models import EmailSender
            
            senders = EmailSender.objects.all().order_by('key')
            senders_data = []
            
            for sender in senders:
                senders_data.append({
                    'id': sender.id,
                    'key': sender.key,
                    'name': sender.name,
                    'email': sender.email,
                    'domain': sender.domain,
                    'is_active': sender.is_active,
                    'display_name': f"{sender.name} ({sender.email})",  # Add display_name field
                    'api_key': sender.api_key,  # Show actual API key
                    'webhook_url': sender.webhook_url,  # Show actual webhook URL
                    'webhook_secret': sender.webhook_secret,  # Show actual webhook secret
                    'created_at': sender.created_at.isoformat(),
                    'updated_at': sender.updated_at.isoformat()
                })
            
            return JsonResponse({
                'success': True,
                'senders': senders_data
            })
            
        except Exception as e:
            logger.error(f"Error fetching email senders: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': f'Failed to fetch email senders: {str(e)}'
            }, status=500)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)


@csrf_exempt
def available_senders_api(request):
    """API to get available active senders for frontend dropdowns"""
    if request.method == 'GET':
        try:
            from .models import EmailSender
            from django.conf import settings
            
            # Get active senders from database
            db_senders = EmailSender.objects.filter(is_active=True).order_by('key')
            senders_data = []
            
            if db_senders.exists():
                # Use database senders
                for sender in db_senders:
                    senders_data.append({
                        'key': sender.key,
                        'name': sender.name,
                        'email': sender.email,
                        'display_name': f"{sender.name} ({sender.email})"
                    })
            else:
                # Fallback to settings if no database senders
                email_senders = getattr(settings, 'EMAIL_SENDERS', {})
                for key, config in email_senders.items():
                    senders_data.append({
                        'key': key,
                        'name': config['name'],
                        'email': config['email'],
                        'display_name': f"{config['name']} ({config['email']})"
                    })
            
            return JsonResponse({
                'success': True,
                'senders': senders_data
            })
            
        except Exception as e:
            logger.error(f"Error fetching available senders: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': f'Failed to fetch available senders: {str(e)}'
            }, status=500)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)


@csrf_exempt
def create_email_sender_api(request):
    """API to create a new email sender"""
    if request.method == 'POST':
        try:
            from .models import EmailSender
            data = json.loads(request.body)
            
            # Validate required fields
            required_fields = ['key', 'name', 'email', 'domain', 'api_key']
            for field in required_fields:
                if not data.get(field):
                    return JsonResponse({
                        'success': False,
                        'error': f'Missing required field: {field}'
                    }, status=400)
            
            # Check if key already exists
            if EmailSender.objects.filter(key=data['key']).exists():
                return JsonResponse({
                    'success': False,
                    'error': 'A sender with this key already exists'
                }, status=400)
            
            # Validate email format
            from django.core.validators import validate_email
            from django.core.exceptions import ValidationError
            try:
                validate_email(data['email'])
            except ValidationError:
                return JsonResponse({
                    'success': False,
                    'error': 'Invalid email format'
                }, status=400)
            
            # Create new email sender
            sender = EmailSender.objects.create(
                key=data['key'],
                name=data['name'],
                email=data['email'],
                domain=data['domain'],
                api_key=data['api_key'],
                webhook_url=data.get('webhook_url', ''),
                webhook_secret=data.get('webhook_secret', ''),
                is_active=data.get('is_active', True)
            )
            
            return JsonResponse({
                'success': True,
                'message': 'Email sender created successfully',
                'sender': {
                    'id': sender.id,
                    'key': sender.key,
                    'name': sender.name,
                    'email': sender.email,
                    'domain': sender.domain,
                    'is_active': sender.is_active
                }
            })
            
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'error': 'Invalid JSON data'
            }, status=400)
        except Exception as e:
            logger.error(f"Error creating email sender: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': f'Failed to create email sender: {str(e)}'
            }, status=500)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)


@csrf_exempt
def update_email_sender_api(request, sender_id):
    """API to update an existing email sender"""
    if request.method == 'PUT':
        try:
            from .models import EmailSender
            data = json.loads(request.body)
            
            # Get the sender
            try:
                sender = EmailSender.objects.get(id=sender_id)
            except EmailSender.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'error': 'Email sender not found'
                }, status=404)
            
            # Update fields if provided
            if 'name' in data:
                sender.name = data['name']
            if 'email' in data:
                # Validate email format
                from django.core.validators import validate_email
                from django.core.exceptions import ValidationError
                try:
                    validate_email(data['email'])
                    sender.email = data['email']
                except ValidationError:
                    return JsonResponse({
                        'success': False,
                        'error': 'Invalid email format'
                    }, status=400)
            if 'domain' in data:
                sender.domain = data['domain']
            if 'api_key' in data:
                sender.api_key = data['api_key']
            if 'webhook_url' in data:
                sender.webhook_url = data['webhook_url']
            if 'webhook_secret' in data:
                sender.webhook_secret = data['webhook_secret']
            if 'is_active' in data:
                sender.is_active = data['is_active']
            
            sender.save()
            
            return JsonResponse({
                'success': True,
                'message': 'Email sender updated successfully',
                'sender': {
                    'id': sender.id,
                    'key': sender.key,
                    'name': sender.name,
                    'email': sender.email,
                    'domain': sender.domain,
                    'is_active': sender.is_active
                }
            })
            
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'error': 'Invalid JSON data'
            }, status=400)
        except Exception as e:
            logger.error(f"Error updating email sender: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': f'Failed to update email sender: {str(e)}'
            }, status=500)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)


@csrf_exempt
def delete_email_sender_api(request, sender_id):
    """API to delete an email sender"""
    if request.method == 'DELETE':
        try:
            from .models import EmailSender
            
            # Get the sender
            try:
                sender = EmailSender.objects.get(id=sender_id)
            except EmailSender.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'error': 'Email sender not found'
                }, status=404)
            
            # Store sender info for response
            sender_info = {
                'key': sender.key,
                'name': sender.name,
                'email': sender.email
            }
            
            # Delete the sender
            sender.delete()
            
            return JsonResponse({
                'success': True,
                'message': f'Email sender "{sender_info["name"]}" deleted successfully'
            })
            
        except Exception as e:
            logger.error(f"Error deleting email sender: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': f'Failed to delete email sender: {str(e)}'
            }, status=500)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)


@csrf_exempt
def export_email_senders_json(request):
    """API to export all email senders as JSON"""
    if request.method == 'GET':
        try:
            from .models import EmailSender
            
            # Get all active senders
            senders = EmailSender.objects.filter(is_active=True)
            
            # Build JSON structure like the settings format
            senders_json = {}
            for sender in senders:
                senders_json[sender.key] = {
                    'email': sender.email,
                    'name': sender.name,
                    'api_key': sender.api_key,
                    'domain': sender.domain,
                    'webhook_url': sender.webhook_url,
                    'webhook_secret': sender.webhook_secret
                }
            
            return JsonResponse({
                'success': True,
                'senders': senders_json
            })
            
        except Exception as e:
            logger.error(f"Error exporting email senders: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': f'Failed to export email senders: {str(e)}'
            }, status=500)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)


@csrf_exempt
def import_email_senders_json(request):
    """API to import email senders from JSON"""
    if request.method == 'POST':
        try:
            from .models import EmailSender
            
            # Parse JSON data
            data = json.loads(request.body)
            senders_data = data.get('senders', {})
            replace_existing = data.get('replace_existing', False)
            
            if not senders_data:
                return JsonResponse({
                    'success': False,
                    'error': 'No senders data provided'
                }, status=400)
            
            created_count = 0
            updated_count = 0
            errors = []
            
            # If replace_existing is True, deactivate all existing senders
            if replace_existing:
                EmailSender.objects.all().update(is_active=False)
            
            # Process each sender
            for key, sender_data in senders_data.items():
                try:
                    # Validate required fields
                    required_fields = ['email', 'name', 'api_key', 'domain']
                    missing_fields = [field for field in required_fields if not sender_data.get(field)]
                    
                    if missing_fields:
                        errors.append(f"Sender '{key}': Missing required fields: {', '.join(missing_fields)}")
                        continue
                    
                    # Check if sender with this key already exists
                    try:
                        sender = EmailSender.objects.get(key=key)
                        # Update existing sender
                        sender.email = sender_data['email']
                        sender.name = sender_data['name']
                        sender.api_key = sender_data['api_key']
                        sender.domain = sender_data['domain']
                        sender.webhook_url = sender_data.get('webhook_url', '')
                        sender.webhook_secret = sender_data.get('webhook_secret', '')
                        sender.is_active = True
                        sender.save()
                        updated_count += 1
                        
                    except EmailSender.DoesNotExist:
                        # Create new sender
                        sender = EmailSender.objects.create(
                            key=key,
                            email=sender_data['email'],
                            name=sender_data['name'],
                            api_key=sender_data['api_key'],
                            domain=sender_data['domain'],
                            webhook_url=sender_data.get('webhook_url', ''),
                            webhook_secret=sender_data.get('webhook_secret', ''),
                            is_active=True
                        )
                        created_count += 1
                        
                except Exception as e:
                    errors.append(f"Sender '{key}': {str(e)}")
                    continue
            
            # Prepare response
            response_data = {
                'success': True,
                'message': f'Import completed. Created: {created_count}, Updated: {updated_count}',
                'created': created_count,
                'updated': updated_count
            }
            
            if errors:
                response_data['errors'] = errors
                response_data['message'] += f', Errors: {len(errors)}'
            
            return JsonResponse(response_data)
            
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'error': 'Invalid JSON format'
            }, status=400)
        except Exception as e:
            logger.error(f"Error importing email senders: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': f'Failed to import email senders: {str(e)}'
            }, status=500)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)
