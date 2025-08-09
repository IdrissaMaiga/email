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
    """Model to store contacts from CSV with their email status"""
    
    EMAIL_STATUS_CHOICES = [
        ('not_sent', 'Not Sent Yet'),
        ('sent', 'Sent'),
        ('delivered', 'Delivered'),
        ('opened', 'Opened'),
        ('clicked', 'Clicked'),
        ('bounced', 'Bounced'),
        ('complained', 'Complained'),
        ('failed', 'Failed'),
    ]
    
    # Contact information from CSV
    first_name = models.CharField(max_length=100, blank=True, null=True)
    last_name = models.CharField(max_length=100, blank=True, null=True)
    email = models.EmailField(unique=True, help_text="Primary email address")
    
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
    emailsender = models.CharField(max_length=100, blank=True, null=True)
    websitecontent = models.TextField(blank=True, null=True)
    leadscore = models.CharField(max_length=50, blank=True, null=True)
    esp = models.CharField(max_length=50, blank=True, null=True, help_text="Email Service Provider")
    
    # Email status tracking
    email_status = models.CharField(max_length=20, choices=EMAIL_STATUS_CHOICES, default='not_sent')
    last_email_sent = models.DateTimeField(blank=True, null=True)
    last_opened = models.DateTimeField(blank=True, null=True)
    last_clicked = models.DateTimeField(blank=True, null=True)
    
    # Tracking
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Store raw CSV data
    csv_data = models.JSONField(blank=True, null=True, help_text="Complete CSV row data")
    
    class Meta:
        ordering = ['last_name', 'first_name']
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['email_status']),
            models.Index(fields=['last_name', 'first_name']),
        ]
    
    def __str__(self):
        name = f"{self.first_name} {self.last_name}".strip()
        return f"{name} ({self.email})" if name else self.email
    
    @property
    def full_name(self):
        """Returns the full name of the contact"""
        return f"{self.first_name} {self.last_name}".strip()
    
    @property
    def display_status(self):
        """Returns a human-readable status"""
        return dict(self.EMAIL_STATUS_CHOICES).get(self.email_status, self.email_status)


class EmailCampaign(models.Model):
    """Model to track email campaigns"""
    
    name = models.CharField(max_length=200, help_text="Campaign name")
    subject = models.TextField(help_text="Email subject used")
    template = models.TextField(help_text="Email template used")
    created_at = models.DateTimeField(default=timezone.now)
    sent_count = models.IntegerField(default=0, help_text="Total emails sent")
    delivered_count = models.IntegerField(default=0, help_text="Total emails delivered")
    opened_count = models.IntegerField(default=0, help_text="Total emails opened")
    clicked_count = models.IntegerField(default=0, help_text="Total emails clicked")
    bounced_count = models.IntegerField(default=0, help_text="Total emails bounced")
    complained_count = models.IntegerField(default=0, help_text="Total complaints")
    failed_count = models.IntegerField(default=0, help_text="Total failed emails")
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} ({self.created_at.date()})"
    
    @property
    def delivery_rate(self):
        """Calculate delivery rate as percentage"""
        if self.sent_count == 0:
            return 0
        return round((self.delivered_count / self.sent_count) * 100, 2)
    
    @property
    def open_rate(self):
        """Calculate open rate as percentage"""
        if self.delivered_count == 0:
            return 0
        return round((self.opened_count / self.delivered_count) * 100, 2)
    
    @property
    def click_rate(self):
        """Calculate click rate as percentage"""
        if self.delivered_count == 0:
            return 0
        return round((self.clicked_count / self.delivered_count) * 100, 2)
    
    @property
    def bounce_rate(self):
        """Calculate bounce rate as percentage"""
        if self.sent_count == 0:
            return 0
        return round((self.bounced_count / self.sent_count) * 100, 2)
