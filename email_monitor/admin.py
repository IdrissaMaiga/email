from django.contrib import admin
from .models import EmailEvent, EmailCampaign, Contact, EmailTemplate, EmailSender

# Register your models here.

@admin.register(EmailEvent)
class EmailEventAdmin(admin.ModelAdmin):
    list_display = ['event_id', 'event_type', 'to_email', 'from_email', 'created_at']
    list_filter = ['event_type', 'created_at']
    search_fields = ['to_email', 'from_email', 'event_id']
    readonly_fields = ['created_at']

@admin.register(EmailCampaign)
class EmailCampaignAdmin(admin.ModelAdmin):
    list_display = ['id', 'session_id', 'status', 'total_contacts', 'emails_sent', 'emails_failed', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['session_id']
    readonly_fields = ['created_at', 'updated_at']

@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ['id', 'email', 'first_name', 'last_name', 'company_name', 'category_name', 'created_at']
    list_filter = ['category_name', 'created_at']
    search_fields = ['email', 'first_name', 'last_name', 'company_name']
    readonly_fields = ['created_at']

@admin.register(EmailTemplate)
class EmailTemplateAdmin(admin.ModelAdmin):
    list_display = ['id', 'template_type', 'sender', 'subject', 'updated_at']
    search_fields = ['sender', 'subject']
    readonly_fields = ['updated_at']

@admin.register(EmailSender)
class EmailSenderAdmin(admin.ModelAdmin):
    list_display = ['key', 'name', 'email', 'domain', 'is_active', 'created_at']
    list_filter = ['is_active', 'domain', 'created_at']
    search_fields = ['key', 'name', 'email', 'domain']
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = (
        ('Basic Information', {
            'fields': ('key', 'name', 'email', 'domain', 'is_active')
        }),
        ('API Configuration', {
            'fields': ('api_key', 'webhook_url', 'webhook_secret')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
