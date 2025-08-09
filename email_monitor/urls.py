from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='email_dashboard'),
    path('contacts/', views.contacts_list, name='contacts_list'),
    path('webhook/', views.webhook_endpoint, name='webhook_endpoint'),
    path('api/contact_email_content/', views.contact_email_content_api, name='contact_email_content_api'),
    path('api/contact_stats/', views.contact_stats_api, name='contact_stats_api'),
]
