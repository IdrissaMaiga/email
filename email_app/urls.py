from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('send_emails/', views.send_emails, name='send_emails'),
    path('api/contact_stats/', views.contact_stats_api, name='contact_stats_api'),
]
