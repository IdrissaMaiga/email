from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('send_emails/', views.send_emails, name='send_emails'),
    path('api/contact_stats/', views.contact_stats_api, name='contact_stats_api'),
    path('api/get_template/', views.get_last_template, name='get_last_template'),
    path('api/save_template/', views.save_template, name='save_template'),
]
