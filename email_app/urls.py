from django.urls import path
from . import views
from .views import get_campaign_progress

urlpatterns = [
    path('', views.index, name='index'),
    path('sender-management/', views.sender_management, name='sender_management'),
    path('send_emails/', views.send_emails, name='send_emails'),
    path('api/contact_stats/', views.contact_stats_api, name='contact_stats_api'),
    path('api/get_template/', views.get_last_template, name='get_last_template'),
    path('api/save_template/', views.save_template, name='save_template'),
    path('api/get_senders/', views.get_senders_api, name='get_senders_api'),
    path('api/campaign-progress/', get_campaign_progress, name='get_campaign_progress'),
]
