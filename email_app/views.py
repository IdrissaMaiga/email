from django.shortcuts import render
from django.http import JsonResponse
from django.conf import settings
from django.utils import timezone
import pandas as pd
import re
import os
import json
import resend
from email_monitor.models import Contact, EmailTemplate
from email_monitor.views import get_sender_email

# Store CSV data in memory (for simplicity; could use database or session for persistence)
csv_data = None
csv_columns = []

def get_email_senders():
    """Get email senders from database with fallback to settings"""
    try:
        from email_monitor.models import EmailSender
        
        # Get active senders from database
        db_senders = EmailSender.objects.filter(is_active=True)
        senders_dict = {}
        
        for sender in db_senders:
            senders_dict[sender.key] = {
                'email': sender.email,
                'name': sender.name,
                'api_key': sender.api_key,
                'domain': sender.domain,
                'webhook_url': sender.webhook_url,
                'webhook_secret': sender.webhook_secret
            }
        
        # If no database senders, fallback to settings
        if not senders_dict:
            senders_dict = getattr(settings, 'EMAIL_SENDERS', {})
        
        return senders_dict
        
    except Exception as e:
        # Fallback to settings if database error
        return getattr(settings, 'EMAIL_SENDERS', {})

def index(request):
    """Render the main email templater page"""
    return render(request, 'email_app/index.html')

def sender_management(request):
    """Render the sender management page"""
    return render(request, 'email_app/sender_management.html')

def get_last_template(request):
    """Get the last used email template for a specific sender"""
    if request.method != 'GET':
        return JsonResponse({'error': 'Only GET method allowed'}, status=405)
    
    try:
        sender = request.GET.get('sender')
        if not sender:
            return JsonResponse({'error': 'Sender parameter is required'}, status=400)
            
        template = EmailTemplate.get_last_used_template(sender)
        return JsonResponse({
            'subject': template.subject,
            'content': template.content,
            'sender': template.sender,
            'updated_at': template.updated_at.isoformat()
        })
    except Exception as e:
        return JsonResponse({'error': f'Failed to load template: {str(e)}'}, status=500)

def save_template(request):
    """Save the current template as the last used one for a specific sender"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST method allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        subject = data.get('subject', '')
        content = data.get('content', '')
        sender = data.get('sender')
        
        if not sender:
            return JsonResponse({'error': 'Sender parameter is required'}, status=400)
        
        if not content:
            return JsonResponse({'error': 'Template content is required'}, status=400)
        
        template = EmailTemplate.save_last_used_template(sender, subject, content)
        return JsonResponse({
            'message': 'Template saved successfully',
            'sender': template.sender,
            'updated_at': template.updated_at.isoformat()
        })
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        return JsonResponse({'error': f'Failed to save template: {str(e)}'}, status=500)

def send_emails(request):
    """Send emails using Resend API with click and open tracking enabled and real-time WebSocket progress"""
    from email_monitor.models import Contact
    import uuid
    import time
    from asgiref.sync import async_to_sync
    from channels.layers import get_channel_layer
    
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST method allowed'}, status=405)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    
    template = data.get('template', '')
    subject = data.get('subject', 'Custom Email')
    contact_filter = data.get('contact_filter')  # Filter contacts by status (optional for custom selection)
    category_filter = data.get('category_filter')  # Filter contacts by category
    contact_limit = data.get('contact_limit')  # Limit number of contacts to send to (deprecated, use range instead)
    contact_range_start = data.get('contact_range_start')  # Start ID for contact range
    contact_range_end = data.get('contact_range_end')  # End ID for contact range
    selected_contact_ids = data.get('selected_contact_ids')  # Custom selection of contact IDs
    sender_key = data.get('sender')  # Which sender to use
    session_id = data.get('session_id') or str(uuid.uuid4())  # WebSocket session ID
    email_timeout = data.get('email_timeout', 30)  # Timeout per email (adjustable)
    batch_size = data.get('batch_size', 10)  # Emails per batch
    batch_delay = data.get('batch_delay', 1)  # Delay between batches
    
    # Initialize WebSocket broadcasting
    channel_layer = get_channel_layer()
    room_group_name = f'email_progress_{session_id}'
    
    def broadcast_progress(message_type, data_dict):
        """Broadcast progress update via WebSocket"""
        if channel_layer:
            async_to_sync(channel_layer.group_send)(
                room_group_name,
                {
                    'type': 'progress_update',
                    'message_type': message_type,
                    'data': data_dict
                }
            )
    
    if not sender_key:
        return JsonResponse({
            'error': 'Sender parameter is required'
        }, status=400)
    
    # Get sender configuration from database or settings
    email_senders = get_email_senders()
    if sender_key not in email_senders:
        return JsonResponse({
            'error': f'Invalid sender selection: {sender_key}'
        }, status=400)
    
    sender_config = email_senders[sender_key]
    api_key = sender_config['api_key']
    from_email = sender_config['email']
    sender_name = sender_config['name']
    
    # Validation
    if not template:
        return JsonResponse({
            'error': 'Missing email template'
        }, status=400)
    
    if not api_key:
        return JsonResponse({
            'error': 'Resend API key not configured in environment'
        }, status=500)
    
    # Get contacts based on selection method
    # Get sender email using the dynamic system
    sender_email = get_sender_email(sender_key)
    
    if selected_contact_ids:
        # Custom selection: get contacts by IDs (no sender filtering needed)
        contacts = Contact.objects.filter(id__in=selected_contact_ids)
        if not contacts.exists():
            return JsonResponse({
                'error': 'No contacts found with the selected IDs'
            }, status=400)
    else:
        # Filter-based selection: get contacts by status filter from this sender
        if not contact_filter:
            contact_filter = 'not_sent'  # Default filter
        
        # Get ALL contacts first (contacts are independent of senders)
        contacts = Contact.objects.all()
        
        # Filter by email status based on LATEST EmailEvent records only
        if contact_filter != 'all':
            from email_monitor.models import EmailEvent
            from django.db.models import Exists, OuterRef, Subquery
            
            if contact_filter == 'not_sent':
                # Contacts with no email events from this sender at all
                any_events = EmailEvent.objects.filter(
                    to_email=OuterRef('email'),
                    from_email__icontains=sender_email
                )
                contacts = contacts.filter(~Exists(any_events))
            else:
                # For all other filters, we need to check the latest event type
                # Get the most recent email event for each contact from this sender
                latest_event_subquery = EmailEvent.objects.filter(
                    to_email=OuterRef('email'),
                    from_email__icontains=sender_email
                ).order_by('-created_at').values('event_type')[:1]
                
                # Annotate contacts with their latest event type from this sender
                contacts = contacts.annotate(
                    latest_event_type=Subquery(latest_event_subquery)
                )
                
                # Filter based on the specific event type
                if contact_filter == 'sent':
                    contacts = contacts.filter(latest_event_type='email.sent')
                elif contact_filter == 'delivered':
                    contacts = contacts.filter(latest_event_type='email.delivered')
                elif contact_filter == 'opened':
                    contacts = contacts.filter(latest_event_type='email.opened')
                elif contact_filter == 'clicked':
                    contacts = contacts.filter(latest_event_type='email.clicked')
                elif contact_filter == 'bounced':
                    contacts = contacts.filter(latest_event_type='email.bounced')
                elif contact_filter == 'failed':
                    contacts = contacts.filter(latest_event_type='email.failed')
                elif contact_filter == 'complained':
                    contacts = contacts.filter(latest_event_type='email.complained')
        
        # Apply category filter if specified
        if category_filter:
            contacts = contacts.filter(category_id=category_filter)
        
        # Apply ID range filter if specified
        if contact_range_start or contact_range_end:
            if contact_range_start and contact_range_end:
                # Both start and end specified
                contacts = contacts.filter(id__gte=contact_range_start, id__lte=contact_range_end)
            elif contact_range_start:
                # Only start specified (from start onwards)
                contacts = contacts.filter(id__gte=contact_range_start)
            elif contact_range_end:
                # Only end specified (from 1 to end)
                contacts = contacts.filter(id__lte=contact_range_end)
        
        # Apply legacy limit if specified and no range is used (for backward compatibility)
        elif contact_limit and isinstance(contact_limit, int) and contact_limit > 0:
            contacts = contacts[:contact_limit]
        
        # Order by ID for consistent results
        contacts = contacts.order_by('id')
        
        if not contacts.exists():
            range_info = ""
            if contact_range_start or contact_range_end:
                if contact_range_start and contact_range_end:
                    range_info = f" in ID range {contact_range_start}-{contact_range_end}"
                elif contact_range_start:
                    range_info = f" from ID {contact_range_start} onwards"
                elif contact_range_end:
                    range_info = f" up to ID {contact_range_end}"
            
            category_info = f" in category '{category_filter}'" if category_filter else ""
            
            return JsonResponse({
                'error': f'No contacts found with status "{contact_filter}"{category_info}{range_info}'
            }, status=400)
    
    # Configure Resend
    resend.api_key = api_key
    
    try:
        contacts_list = list(contacts)
        total_contacts = len(contacts_list)
        
        # Broadcast campaign start
        broadcast_progress('campaign_start', {
            'total_contacts': total_contacts,
            'batch_size': batch_size,
            'sender': f"{sender_name} <{from_email}>",
            'subject': subject
        })
        
        emails_sent = 0
        failed_emails = []
        
        # Process contacts in batches
        for batch_num in range(0, total_contacts, batch_size):
            current_batch = batch_num // batch_size + 1
            batch_start = batch_num + 1
            batch_end = min(batch_num + batch_size, total_contacts)
            batch_contacts = contacts_list[batch_num:batch_num + batch_size]
            
            # Broadcast batch start
            broadcast_progress('batch_start', {
                'batch_number': current_batch,
                'batch_size': len(batch_contacts),
                'batch_start': batch_start,
                'batch_end': batch_end
            })
            
            batch_sent = 0
            
            for i, contact in enumerate(batch_contacts):
                contact_index = batch_num + i + 1
                progress_percent = round((contact_index / total_contacts) * 100)
                
                recipient_email = contact.email.strip()
                if not recipient_email:
                    continue

                # Validate email format
                import re
                email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
                if not re.match(email_pattern, recipient_email):
                    failed_emails.append(f"{recipient_email}: Invalid email format")
                    broadcast_progress('email_error', {
                        'contact_email': recipient_email,
                        'contact_name': contact.full_name,
                        'error': 'Invalid email format',
                        'progress_percent': progress_percent
                    })
                    continue

                # Broadcast email start
                broadcast_progress('email_start', {
                    'contact_email': recipient_email,
                    'contact_name': contact.full_name,
                    'contact_id': contact.id,
                    'progress_percent': progress_percent
                })

                # Create contact data dictionary for template replacement
                contact_data = {
                    'prospect_first_name': contact.first_name or '',
                    'prospect_last_name': contact.last_name or '',
                    'company_name': contact.company_name or '',
                    'job_title': contact.job_title or '',
                    'prospect_location_city': contact.location_city or '',
                    'prospect_location_country': contact.location_country or '',
                    'company_industry': contact.company_industry or '',
                    'company_website': contact.company_website or '',
                    'linkedin_url': contact.linkedin_url or '',
                    'linkedin_headline': contact.linkedin_headline or '',
                    'phone_number': contact.phone_number or '',
                    'tailored_tone_first_line': contact.tailored_tone_first_line or '',
                    'tailored_tone_ps_statement': contact.tailored_tone_ps_statement or '',
                    'tailored_tone_subject': contact.tailored_tone_subject or '',
                    'custom_ai_1': contact.custom_ai_1 or '',
                    'custom_ai_2': contact.custom_ai_2 or '',
                    'company_description': contact.company_description or '',
                    'websitecontent': contact.websitecontent or '',
                    # Add full name for convenience
                    'full_name': contact.full_name,
                }

                # Replace placeholders in template (HTML content)
                email_html_content = template

                # Find placeholders in template
                placeholders = re.findall(r'\{(.*?)\}', template)
                
                for placeholder in placeholders:
                    value = contact_data.get(placeholder, f'[{placeholder} not found]')
                    email_html_content = email_html_content.replace(f'{{{placeholder}}}', str(value))
                
                # Create simple plain text version by removing basic HTML tags
                email_text_content = re.sub(r'<[^>]+>', '', email_html_content)
                # Clean up extra whitespace
                email_text_content = re.sub(r'\n\s*\n', '\n\n', email_text_content.strip())
                
                try:
                    # Send email with Resend API
                    params = {
                        "from": f"{sender_name} <{from_email}>" if sender_name else from_email,
                        "to": [recipient_email],
                        "subject": subject,
                        "html": email_html_content,
                        "text": email_text_content,
                        # Enable tracking
                        "tags": [
                            {"name": "campaign", "value": "email_campaign"},
                            {"name": "environment", "value": "production"},
                            {"name": "contact_id", "value": str(contact.id)}
                        ],
                        "headers": {
                            "X-Entity-Ref-ID": f"contact-{contact.id}"
                        }
                    }
                    
                    # Send the email
                    response = resend.Emails.send(params)
                    
                    if response and 'id' in response:
                        emails_sent += 1
                        batch_sent += 1
                        
                        # Broadcast email success
                        broadcast_progress('email_success', {
                            'contact_email': recipient_email,
                            'contact_name': contact.full_name,
                            'contact_id': contact.id,
                            'resend_id': response['id'],
                            'progress_percent': progress_percent
                        })
                        
                        print(f"✅ EMAIL SENT: Successfully sent to {recipient_email} with Resend ID {response['id']}")
                    else:
                        failed_emails.append(recipient_email)
                        broadcast_progress('email_error', {
                            'contact_email': recipient_email,
                            'contact_name': contact.full_name,
                            'error': 'No response ID from Resend',
                            'progress_percent': progress_percent
                        })
                        print(f"❌ EMAIL FAILED: No response ID for {recipient_email}")
                        
                except Exception as email_error:
                    failed_emails.append(f"{recipient_email}: {str(email_error)}")
                    broadcast_progress('email_error', {
                        'contact_email': recipient_email,
                        'contact_name': contact.full_name,
                        'error': str(email_error),
                        'progress_percent': progress_percent
                    })
                    print(f"❌ EMAIL ERROR: {recipient_email}: {str(email_error)}")
                
                # Add delay between emails (respecting timeout setting)
                time.sleep(min(email_timeout / 10, 2))  # Small delay between emails
            
            # Broadcast batch complete
            remaining_contacts = total_contacts - batch_end
            broadcast_progress('batch_complete', {
                'batch_number': current_batch,
                'emails_sent_in_batch': batch_sent,
                'total_sent_so_far': emails_sent,
                'remaining_contacts': remaining_contacts
            })
            
            # Add delay between batches
            if remaining_contacts > 0 and batch_delay > 0:
                time.sleep(batch_delay)
        
        # Broadcast campaign complete
        success_rate = round((emails_sent / total_contacts) * 100) if total_contacts > 0 else 0
        broadcast_progress('campaign_complete', {
            'emails_sent': emails_sent,
            'total_contacts': total_contacts,
            'success_rate': success_rate,
            'failed_count': len(failed_emails)
        })
        
        message = f'Emails sent successfully! ({emails_sent} emails sent with tracking enabled)'
        if failed_emails:
            message += f'. Failed: {len(failed_emails)} emails'
        
        # Save the template as the last used template
        try:
            EmailTemplate.save_last_used_template(sender_key, subject, template)
        except Exception as e:
            print(f"Failed to save template: {e}")  # Log but don't fail the email sending
        
        return JsonResponse({
            'message': message,
            'emails_sent': emails_sent,
            'failed_count': len(failed_emails),
            'failed_emails': failed_emails[:10] if failed_emails else []  # Show first 10 failures
        })
        
    except Exception as e:
        return JsonResponse({
            'error': f'Failed to send emails: {str(e)}'
        }, status=500)


def contact_stats_api(request):
    """API endpoint to get contact statistics"""
    from email_monitor.models import Contact, EmailEvent
    from django.db.models import Subquery, OuterRef
    
    try:
        # Get sender parameter to filter stats by sender
        sender = request.GET.get('sender')
        if not sender:
            return JsonResponse({'error': 'Sender parameter is required'}, status=400)
        
        # Get category parameter to filter stats by category
        category_filter = request.GET.get('category')
        
        # Get sender email using the dynamic system (same as used in email sending)
        sender_email = get_sender_email(sender)
        
        # Get ALL contacts (contacts are independent of senders)
        sender_contacts = Contact.objects.all()
        
        # Apply category filter if specified
        if category_filter and category_filter != 'all':
            print(f"📊 STATS DEBUG: Filtering by category_id = '{category_filter}'")
            sender_contacts = sender_contacts.filter(category_id=category_filter)
            print(f"📊 STATS DEBUG: Contacts after category filter = {sender_contacts.count()}")
        else:
            print(f"📊 STATS DEBUG: No category filter applied, total contacts = {sender_contacts.count()}")
        
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
        
        # Debug: Check what EmailEvents exist for this sender
        total_events = EmailEvent.objects.filter(from_email__icontains=sender_email).count()
        recent_events = EmailEvent.objects.filter(from_email__icontains=sender_email).order_by('-created_at')[:5]
        
        print(f"📊 STATS DEBUG: Stats for category '{category_filter or 'All'}': Total={total_contacts}, NotSent={not_sent_count}, Sent={sent_count}")
        print(f"📊 STATS DEBUG: Total EmailEvents for sender '{sender_email}': {total_events}")
        print(f"📊 STATS DEBUG: Recent EmailEvents:")
        for event in recent_events:
            print(f"  - {event.event_type} to {event.to_email} at {event.created_at}")
        
        # Debug: Show sample contact with latest event
        sample_contact = contacts_with_latest_event.first()
        if sample_contact:
            print(f"📊 STATS DEBUG: Sample contact '{sample_contact.email}' has latest_event_type: {sample_contact.latest_event_type}")
        
        return JsonResponse({
            'total_contacts': total_contacts,
            'total_email_events': contacts_with_latest_event.exclude(latest_event_type__isnull=True).count(),
            'not_sent': not_sent_count,
            'sent': sent_count,
            'delivered': delivered_count,
            'opened': opened_count,
            'clicked': clicked_count,
            'bounced': bounced_count,
            'failed': failed_count,
            'complained': complained_count,
            'sender': sender,
            'sender_email': sender_email,
            'category_filter': category_filter,
            'stats_explanation': {
                'total_contacts': f'Total number of contact records {"in category " + category_filter if category_filter else "(all categories)"}',
                'total_email_events': 'Number of contacts with email events from this sender',
                'status_counts': 'Contact counts based on their latest email status from this sender only',
                'category_filtered': bool(category_filter)
            }
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def get_senders_api(request):
    """Get all active email senders"""
    try:
        from email_monitor.models import EmailSender
        
        # Get active senders from database
        senders = EmailSender.objects.filter(is_active=True).values(
            'key', 'email', 'name', 'domain'
        )
        
        # Convert to dictionary format expected by frontend
        senders_dict = {}
        for sender in senders:
            senders_dict[sender['key']] = {
                'name': sender['name'],  # Use the actual name
                'email': sender['email'],
                'domain': sender['domain'],
                'display_name': f"{sender['name']} ({sender['email']})" if sender['name'] != sender['email'] else sender['email']
            }
        
        return JsonResponse({'senders': senders_dict})
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
