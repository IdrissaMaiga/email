"""
URL configuration for email_sender project.
"""
from django.contrib import admin
from django.urls import path, include
from email_monitor.views import webhook_endpoint

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('email_app.urls')),
    path('monitor/', include('email_monitor.urls')),
    # Webhook endpoint for Resend
    path('webhook', webhook_endpoint, name='webhook_endpoint'),
]
