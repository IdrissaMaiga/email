from django.db import models
from django.utils import timezone
import json


class EmailEvent(models.Model):
    """Model to store email events from Resend webhooks"""
    
    EVENT_TYPES = [
        ('email.sent', 'Email Sent'),
        ('email.delivered', 'Email Delivered'),
        ('email.bounced', 'Email Bounced'),
        ('email.opened', 'Email Opened'),
        ('email.clicked', 'Email Clicked'),
        ('email.complained', 'Email Complained'),
        ('email.failed', 'Email Failed'),
        ('email.delivery_delayed', 'Email Delivery Delayed'),
        ('email.scheduled', 'Email Scheduled'),
        ('contact.created', 'Contact Created'),
        ('contact.updated', 'Contact Updated'),
        ('contact.deleted', 'Contact Deleted'),
        ('domain.created', 'Domain Created'),
        ('domain.updated', 'Domain Updated'),
        ('domain.deleted', 'Domain Deleted'),
    ]
    
    # Basic event information
    event_id = models.CharField(max_length=255, help_text="Event ID from Resend (can be duplicate)")
    event_type = models.CharField(max_length=50, choices=EVENT_TYPES, help_text="Type of event")
    created_at = models.DateTimeField(help_text="When the event occurred")
    received_at = models.DateTimeField(default=timezone.now, help_text="When we received the webhook")
    
    # Email-specific fields
    email_id = models.CharField(max_length=255, blank=True, null=True, help_text="Email ID from Resend")
    from_email = models.EmailField(blank=True, null=True, help_text="Sender email address")
    to_email = models.EmailField(blank=True, null=True, help_text="Recipient email address")
    subject = models.TextField(blank=True, null=True, help_text="Email subject")
    
    # Event-specific data
    click_url = models.URLField(blank=True, null=True, help_text="URL clicked (for click events)")
    bounce_reason = models.TextField(blank=True, null=True, help_text="Reason for bounce")
    complaint_feedback_type = models.CharField(max_length=100, blank=True, null=True, help_text="Type of complaint")
    
    # Raw webhook data
    raw_data = models.JSONField(help_text="Complete webhook payload")
    
    class Meta:
        ordering = ['-received_at']
        indexes = [
            models.Index(fields=['event_type']),
            models.Index(fields=['to_email']),
            models.Index(fields=['created_at']),
            models.Index(fields=['email_id']),
        ]
    
    def __str__(self):
        return f"{self.event_type} - {self.to_email} ({self.created_at})"
    
    @property
    def is_positive_event(self):
        """Returns True for positive events (sent, delivered, opened, clicked)"""
        return self.event_type in ['email.sent', 'email.delivered', 'email.opened', 'email.clicked']
    
    @property
    def is_negative_event(self):
        """Returns True for negative events (bounced, complained, failed)"""
        return self.event_type in ['email.bounced', 'email.complained', 'email.failed']


class Contact(models.Model):
    """Model to store contacts from CSV with category-based ID system"""
    
    # Category and ID fields (with safe defaults for existing data)
    category_id = models.CharField(
        max_length=50, 
        default='1',
        help_text="Auto-generated category identifier (1, 2, 3, etc.)"
    )
    category_name = models.CharField(
        max_length=200, 
        default='Default Category',
        help_text="Human-readable category name"
    )
    contact_id = models.IntegerField(
        default=1,
        help_text="Contact ID within this category (1, 2, 3, etc.)"
    )
    
    # Contact information from CSV - allow duplicate emails for different categories
    first_name = models.CharField(max_length=100, blank=True, null=True)
    last_name = models.CharField(max_length=100, blank=True, null=True)
    email = models.EmailField(help_text="Primary email address")
    
    # Location data
    location_city = models.CharField(max_length=100, blank=True, null=True)
    location_country = models.CharField(max_length=100, blank=True, null=True)
    
    # Company data
    company_name = models.CharField(max_length=200, blank=True, null=True)
    company_industry = models.CharField(max_length=200, blank=True, null=True)
    company_website = models.URLField(blank=True, null=True)
    company_description = models.TextField(blank=True, null=True)
    company_linkedin_url = models.URLField(blank=True, null=True)
    company_headcount = models.CharField(max_length=50, blank=True, null=True)
    
    # Professional data
    job_title = models.CharField(max_length=200, blank=True, null=True)
    linkedin_url = models.URLField(blank=True, null=True)
    linkedin_headline = models.CharField(max_length=300, blank=True, null=True)
    linkedin_position = models.CharField(max_length=200, blank=True, null=True)
    linkedin_summary = models.TextField(blank=True, null=True)
    phone_number = models.CharField(max_length=50, blank=True, null=True)
    
    # Campaign data
    tailored_tone_first_line = models.TextField(blank=True, null=True)
    tailored_tone_ps_statement = models.TextField(blank=True, null=True)
    tailored_tone_subject = models.CharField(max_length=300, blank=True, null=True)
    custom_ai_1 = models.TextField(blank=True, null=True)
    custom_ai_2 = models.TextField(blank=True, null=True)
    
    # Media data
    profile_image_url = models.URLField(blank=True, null=True)
    logo_image_url = models.URLField(blank=True, null=True)
    
    # Funnel and tracking data
    funnel_unique_id = models.CharField(max_length=100, blank=True, null=True)
    funnel_step = models.CharField(max_length=50, blank=True, null=True)
    sequence_unique_id = models.CharField(max_length=100, blank=True, null=True)
    variation_unique_id = models.CharField(max_length=100, blank=True, null=True)
    websitecontent = models.TextField(blank=True, null=True)
    leadscore = models.CharField(max_length=50, blank=True, null=True)
    esp = models.CharField(max_length=50, blank=True, null=True, help_text="Email Service Provider")
    
    # Tracking
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Store raw CSV data
    csv_data = models.JSONField(blank=True, null=True, help_text="Complete CSV row data")
    
    class Meta:
        ordering = ['category_id', 'contact_id']
        indexes = [
            models.Index(fields=['category_id', 'contact_id']),
            models.Index(fields=['email']),
            models.Index(fields=['last_name', 'first_name']),
            models.Index(fields=['category_name']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['category_id', 'contact_id'], 
                name='unique_contact_per_category'
            ),
            models.UniqueConstraint(
                fields=['category_id', 'email'], 
                name='unique_email_per_category'
            ),
        ]
    
    def __str__(self):
        name = f"{self.first_name} {self.last_name}".strip()
        contact_info = f"{name} ({self.email})" if name else self.email
        return f"[{self.category_id}#{self.contact_id}] {contact_info}"
    
    @property
    def full_name(self):
        """Returns the full name of the contact"""
        return f"{self.first_name} {self.last_name}".strip()


class EmailTemplate(models.Model):
    """Model to store email templates for each sender"""
    
    TEMPLATE_TYPES = [
        ('default', 'Default Template'),
        ('last_used', 'Last Used Template'),
    ]
    
    template_type = models.CharField(max_length=20, choices=TEMPLATE_TYPES, 
                                   help_text="Type of template (default or last used)")
    sender = models.CharField(max_length=50, 
                            help_text="Sender identifier")
    subject = models.TextField(default="EU Grant Advisory Platform - Beta Testing Invitation", 
                              help_text="Email subject")
    content = models.TextField(help_text="Email template content")
    updated_at = models.DateTimeField(default=timezone.now, help_text="When template was last updated")
    
    class Meta:
        ordering = ['-updated_at']
        unique_together = [('template_type', 'sender')]  # Ensure unique template per sender per type
    
    def __str__(self):
        return f"{self.get_template_type_display()} - {self.sender} - {self.subject[:50]}"
    
    @classmethod
    def get_last_used_template(cls, sender):
        """Get the last used template for a specific sender"""
        if not sender:
            raise ValueError("Sender parameter is required")
            
        try:
            # Get the most recent 'last_used' template for this sender
            template = cls.objects.filter(
                sender=sender, 
                template_type='last_used'
            ).order_by('-updated_at').first()
            
            if template:
                return template
            else:
                # Create a new empty template for this sender
                return cls.objects.create(
                    template_type='last_used',
                    sender=sender,
                    subject='',
                    content=''
                )
        except Exception as e:
            # Create a new empty template for this sender if any error occurs
            return cls.objects.create(
                template_type='last_used',
                sender=sender,
                subject='',
                content=''
            )

    @classmethod
    def save_last_used_template(cls, sender, subject, content):
        """Save the template as the last used one for a specific sender"""
        template, created = cls.objects.get_or_create(
            template_type='last_used',
            sender=sender,
            defaults={'subject': subject, 'content': content}
        )
        if not created:
            template.subject = subject
            template.content = content
            template.updated_at = timezone.now()
            template.save()
        return template


class EmailSender(models.Model):
    """Model to store dynamic email sender configurations"""
    
    # Basic sender information
    key = models.CharField(max_length=50, unique=True, help_text="Unique identifier for this sender")
    email = models.EmailField(help_text="Sender email address")
    name = models.CharField(max_length=255, help_text="Display name for the sender")
    domain = models.CharField(max_length=255, help_text="Domain for this sender")
    
    # Resend API configuration
    api_key = models.CharField(max_length=255, help_text="Resend API key")
    
    # Webhook configuration
    webhook_url = models.CharField(max_length=500, help_text="Webhook URL for this sender")
    webhook_secret = models.CharField(max_length=255, help_text="Webhook secret for verification")
    
    # Status and metadata
    is_active = models.BooleanField(default=True, help_text="Whether this sender is active")
    is_verified = models.BooleanField(default=False, help_text="Whether the domain is verified with Resend")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Usage statistics
    emails_sent = models.PositiveIntegerField(default=0, help_text="Total emails sent using this sender")
    last_used = models.DateTimeField(null=True, blank=True, help_text="When this sender was last used")
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Email Sender"
        verbose_name_plural = "Email Senders"
    
    def __str__(self):
        return f"{self.name} <{self.email}>"
    
    def increment_usage(self):
        """Increment usage counter and update last used timestamp"""
        self.emails_sent += 1
        self.last_used = timezone.now()
        self.save(update_fields=['emails_sent', 'last_used'])
    
    @classmethod
    def get_active_senders(cls):
        """Get all active sender configurations"""
        return cls.objects.filter(is_active=True).order_by('name')
    
    @classmethod
    def get_sender_config(cls, sender_key):
        """Get sender configuration in the format expected by the email sending code"""
        try:
            sender = cls.objects.get(key=sender_key, is_active=True)
            return {
                'email': sender.email,
                'name': sender.name,
                'api_key': sender.api_key,
                'domain': sender.domain,
                'webhook_url': sender.webhook_url,
                'webhook_secret': sender.webhook_secret
            }
        except cls.DoesNotExist:
            return None
    
    @classmethod
    def get_all_sender_configs(cls):
        """Get all active sender configurations in the format expected by the email sending code"""
        configs = {}
        for sender in cls.get_active_senders():
            configs[sender.key] = {
                'email': sender.email,
                'name': sender.name,
                'api_key': sender.api_key,
                'domain': sender.domain,
                'webhook_url': sender.webhook_url,
                'webhook_secret': sender.webhook_secret
            }
        return configs


class EmailCampaign(models.Model):
    """Model to track email campaign sessions for progress persistence"""
    
    CAMPAIGN_STATUS = [
        ('preparing', 'Preparing'),
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('paused', 'Paused'),
    ]
    
    # Campaign identification
    session_id = models.CharField(max_length=100, unique=True, help_text="WebSocket session ID")
    campaign_name = models.CharField(max_length=200, blank=True, null=True, help_text="Optional campaign name")
    
    # Campaign configuration
    sender_key = models.CharField(max_length=100, help_text="Sender configuration key")
    subject = models.TextField(help_text="Email subject")
    template = models.TextField(help_text="Email template content")
    
    # Campaign progress
    status = models.CharField(max_length=20, choices=CAMPAIGN_STATUS, default='preparing')
    total_contacts = models.IntegerField(default=0)
    emails_sent = models.IntegerField(default=0)
    emails_failed = models.IntegerField(default=0)
    current_contact_index = models.IntegerField(default=0)
    
    # Timestamps
    created_at = models.DateTimeField(default=timezone.now)
    started_at = models.DateTimeField(blank=True, null=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    
    # Configuration
    email_timeout = models.IntegerField(default=30, help_text="Timeout between emails in seconds")
    
    # Contact selection (JSON field to store the query parameters)
    contact_selection = models.JSONField(default=dict, help_text="Contact filter and selection criteria")
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['session_id']),
            models.Index(fields=['status']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"Campaign {self.session_id} - {self.status} ({self.emails_sent}/{self.total_contacts})"
    
    @property
    def progress_percentage(self):
        """Calculate completion percentage"""
        if self.total_contacts == 0:
            return 0
        return round(((self.emails_sent + self.emails_failed) / self.total_contacts) * 100)
    
    @property
    def success_rate(self):
        """Calculate success rate percentage"""
        total_processed = self.emails_sent + self.emails_failed
        if total_processed == 0:
            return 0
        return round((self.emails_sent / total_processed) * 100)
    
    @classmethod
    def get_active_campaign(cls):
        """Get the currently active campaign if any"""
        return cls.objects.filter(status__in=['preparing', 'running', 'paused']).first()
    
    def mark_as_running(self):
        """Mark campaign as running"""
        self.status = 'running'
        if not self.started_at:
            self.started_at = timezone.now()
        self.save()
    
    def mark_as_completed(self):
        """Mark campaign as completed"""
        self.status = 'completed'
        self.completed_at = timezone.now()
        self.save()
    
    def increment_sent(self):
        """Increment sent email count"""
        self.emails_sent += 1
        self.current_contact_index += 1
        self.save()
    
    def increment_failed(self):
        """Increment failed email count"""
        self.emails_failed += 1
        self.current_contact_index += 1
        self.save()
