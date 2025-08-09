from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.conf import settings
from django.utils import timezone
from django.db.models import Count, Q
from django.core.paginator import Paginator
from .models import EmailEvent, EmailCampaign, Contact
import json
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
        
        resend_api_key = os.getenv('RESEND_API_KEY')
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
def webhook_endpoint(request):
    """
    Resend webhook endpoint to receive email events
    For development: http://127.0.0.1:8000/webhook
    For production: https://email.horizoneurope.io/webhook
    """
    
    try:
        # Parse webhook payload
        raw_body = request.body.decode('utf-8')
        payload = json.loads(raw_body)
        
        # Log the full payload for debugging
        logger.info(f"Received webhook payload: {payload}")
        
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
    """Verify Resend webhook signature"""
    try:
        signature = request.headers.get('Resend-Signature')
        if not signature:
            return False
        
        # Create expected signature
        payload = request.body
        expected_signature = hmac.new(
            signing_secret.encode('utf-8'),
            payload,
            hashlib.sha256
        ).hexdigest()
        
        # Compare signatures
        return hmac.compare_digest(signature, expected_signature)
    except Exception as e:
        logger.error(f"Signature verification error: {str(e)}")
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
