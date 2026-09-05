"""
URL configuration for invywed project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
# Django admin bawaan DIHAPUS - menggunakan custom admin panel saja
# from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponse
from invitation_templates import views as invitation_views
from core import views as core_views
from thema import views as thema_views

def health_check(request):
    """Simple health check endpoint"""
    return HttpResponse("Invywed System Running", content_type="text/plain")

urlpatterns = [
    # Public Home - Langsung di root tanpa /public/
    path('', core_views.home, name='public_home'),
    
    # Public Theme List
    path('tema/', core_views.theme_list, name='public_theme_list'),
    
    # Health check
    path('health/', health_check, name='health_check'),
    
    # Django admin bawaan DIHAPUS - tidak digunakan lagi
    # path('django-admin/', admin.site.urls),
    
    # Django Summernote
    path('summernote/', include('django_summernote.urls')),
    
    # Custom Admin Panel (sekarang di /admin/)
    path('admin/', include('admin_panel.urls')),
    
    # Template editor (requires admin login) - /editor/<slug>/
    path('editor/', include('invitation_templates.urls')),
    
    # Thema (Tema) Management - /demo/<slug>/ untuk public demo
    path('demo/', include('thema.urls')),
    
    # AJAX endpoint untuk filter themes
    path('api/themes/filter/', thema_views.themes_filter_ajax, name='themes_filter_ajax'),
    
    # ===== INVITATION RENDER ENGINE =====
    # Urutan URL penting: yang spesifik di atas, yang general di bawah
    # 1. Owner Preview (harus di atas karena lebih spesifik)
    path('preview/<str:slug>/', invitation_views.preview_invitation, name='preview_invitation'),
    
    # 2. Submit wish (AJAX) - HARUS SEBELUM path general agar tidak tertangkap
    path('<str:invitation_slug>/wish/submit/', invitation_views.submit_wish, name='submit_wish'),
    
    # 3. Guest Specific (spesifik dengan guest_slug)
    path('<str:invitation_slug>/<str:guest_slug>/', invitation_views.render_invitation, name='render_invitation_guest'),
    
    # 4. Public General (general tanpa guest_slug) - HARUS DI BAWAH
    path('<str:invitation_slug>/', invitation_views.render_invitation, name='render_invitation_public'),
    
    # Users App (Mempelai/Klien)
    # users.urls tidak punya path(''), jadi tidak akan menangkap root
    path('', include('users.urls')),
    
    # Future URLs untuk apps lain
    # path('api/', include('api.urls')),
]

# Serve media files during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
