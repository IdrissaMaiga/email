"""
URL configuration for email_sender project.
"""
from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.views.static import serve
from email_monitor.views import webhook_handler_view

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('email_app.urls')),
    path('monitor/', include('email_monitor.urls')),
    # Direct webhook endpoints (no /monitor/ prefix)
    path('webhook/<str:endpoint>/', webhook_handler_view, name='webhook_handler'),
]

# Serve static files in all environments (including production)
urlpatterns += [
    re_path(r'^static/(?P<path>.*)$', serve, {'document_root': settings.STATIC_ROOT}),
]
