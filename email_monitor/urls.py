from django.urls import path
from . import views

urlpatterns = [
    path('', views.contacts_list, name='contacts_list'),
    path('contacts/', views.contacts_list, name='contacts_list_alt'),
    path('contacts/upload/', views.upload_csv, name='upload_csv'),
    path('contacts/delete/<int:contact_id>/', views.delete_contact, name='delete_contact'),
    path('api/contact_email_content/', views.contact_email_content_api, name='contact_email_content_api'),
    path('api/email_content_by_id/', views.email_content_by_id_api, name='email_content_by_id_api'),
    path('api/contact_stats/', views.contact_stats_api, name='contact_stats_api'),
    path('api/contacts/', views.contacts_api, name='contacts_api'),
    path('api/categories/', views.get_categories_api, name='get_categories_api'),
    path('api/add-contact/', views.add_contact_api, name='add_contact_api'),
    path('api/update_contact_field/', views.update_contact_field_api, name='update_contact_field_api'),
    path('api/update_contact_batch/', views.update_contact_batch_api, name='update_contact_batch_api'),
    path('api/reset_database/', views.reset_database_api, name='reset_database_api'),
    # Email Sender Management APIs
    path('api/email_senders/', views.email_senders_api, name='email_senders_api'),
    path('api/email_senders/available/', views.available_senders_api, name='available_senders_api'),
    path('api/email_senders/create/', views.create_email_sender_api, name='create_email_sender_api'),
    path('api/email_senders/<int:sender_id>/update/', views.update_email_sender_api, name='update_email_sender_api'),
    path('api/email_senders/<int:sender_id>/delete/', views.delete_email_sender_api, name='delete_email_sender_api'),
    # JSON Import/Export APIs
    path('api/email_senders/export/', views.export_email_senders_json, name='export_email_senders_json'),
    path('api/email_senders/import/', views.import_email_senders_json, name='import_email_senders_json'),
    # Contacts Export API
    path('api/export_contacts_xls/', views.export_contacts_xls, name='export_contacts_xls'),
]
