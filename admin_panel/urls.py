from django.urls import path, include
from . import views
from thema import views as thema_views

app_name = 'admin_panel'

urlpatterns = [
    # ===== AUTHENTICATION =====
    path('login/', views.admin_login, name='admin_login'),
    path('logout/', views.admin_logout, name='admin_logout'),
    
    # ===== DASHBOARD =====
    path('', views.admin_dashboard, name='dashboard'),
    
    # ===== THEMA MANAGEMENT =====
    path('thema/list/', thema_views.theme_list, name='theme_list'),
    path('thema/upload/', thema_views.theme_upload, name='theme_upload'),
    path('thema/edit/<int:pk>/', thema_views.theme_edit, name='theme_edit'),
    path('thema/delete/<int:pk>/', thema_views.theme_delete, name='theme_delete'),
    path('thema/download/<int:pk>/', thema_views.theme_download, name='theme_download'),
    path('thema/preview/<int:pk>/', thema_views.theme_preview, name='theme_preview'),
    
    # ===== CATEGORY MANAGEMENT =====
    path('thema/category/create/', thema_views.category_create, name='category_create'),
    path('thema/category/update/<int:pk>/', thema_views.category_update, name='category_update'),
    path('thema/category/delete/<int:pk>/', thema_views.category_delete, name='category_delete'),
    path('thema/category/get/<int:pk>/', thema_views.category_get, name='category_get'),
    path('thema/category/list/', thema_views.category_list_ajax, name='category_list_ajax'),
    
    # ===== EDITOR ===== (REMOVED - Theme model deleted)
    
    # ===== INVITATION MANAGEMENT =====
    path('invitations/', views.invitation_list, name='invitation_list'),
    path('invitations/add/', views.invitation_manage, name='invitation_add'),
    path('invitations/edit/<int:pk>/', views.invitation_manage, name='invitation_edit'),
    path('invitations/preview/<slug:slug>/', views.invitation_preview, name='invitation_preview'),
    path('invitations/delete/<int:pk>/', views.invitation_delete, name='invitation_delete'),
    
    # ===== USER MANAGEMENT =====
    path('users/', views.user_list, name='user_list'),
    path('users/<int:pk>/', views.user_detail, name='user_detail'),
    path('users/<int:pk>/toggle-status/', views.user_toggle_status, name='user_toggle_status'),
    
    # ===== CLIENT PROFILES (Users App) =====
    path('clients/', views.client_profile_list, name='client_profile_list'),
    path('clients/<int:pk>/', views.client_profile_detail, name='client_profile_detail'),
    path('clients/<int:pk>/download-json/', views.client_profile_download_json, name='client_profile_download_json'),
    
    # ===== CONTENT MANAGEMENT ===== (REMOVED - not needed for small website)
    # path('blog/', views.blog_list, name='blog_list'),
    
    # ===== SUPPORT TICKETS ===== (REMOVED - not needed for small website)
    # path('tickets/', views.ticket_list, name='ticket_list'),
    
    # ===== PRICING & PACKAGES ===== (REMOVED - not needed for small website)
    # path('packages/', views.pricing_package_list, name='pricing_package_list'),
    # path('packages/<int:pk>/', views.pricing_package_detail, name='pricing_package_detail'),
    # path('coupons/', views.discount_coupon_list, name='discount_coupon_list'),
    # path('payment-methods/', views.payment_method_list, name='payment_method_list'),
    # path('refunds/', views.refund_request_list, name='refund_request_list'),
    
    # ===== CONTENT & MARKETING ===== (REMOVED - not needed for small website)
    # path('testimonials/', views.testimonial_list, name='testimonial_list'),
    # path('faq/', views.faq_list, name='faq_list'),
    # path('vendors/', views.partner_vendor_list, name='partner_vendor_list'),
    
    # ===== WEBSITE SETTINGS ===== (REMOVED - not needed for small website)
    # path('settings/', views.site_configuration, name='site_configuration'),
    # path('maintenance-logs/', views.maintenance_log_list, name='maintenance_log_list'),
    
    # ===== TEMPLATE ASSETS ===== (REMOVED - not needed for small website)
    
    # ===== WHATSAPP MANAGEMENT =====
    path('whatsapp/', views.whatsapp_management, name='whatsapp_management'),
    path('whatsapp/numbers/manage/<int:pk>/', views.whatsapp_number_manage, name='whatsapp_number_manage'),
    path('whatsapp/numbers/manage/', views.whatsapp_number_manage, name='whatsapp_number_add'),
    path('whatsapp/numbers/delete/<int:pk>/', views.whatsapp_number_delete, name='whatsapp_number_delete'),
    path('whatsapp/templates/manage/<int:pk>/', views.whatsapp_template_manage, name='whatsapp_template_manage'),
    path('whatsapp/templates/manage/', views.whatsapp_template_manage, name='whatsapp_template_add'),
    path('whatsapp/templates/delete/<int:pk>/', views.whatsapp_template_delete, name='whatsapp_template_delete'),
    
    # ===== QR MANAGER =====
    path('guests/', views.guest_list, name='guest_list'),
    path('guests/<int:pk>/', views.guest_detail, name='guest_detail'),
    path('guest-groups/', views.guest_group_list, name='guest_group_list'),
    path('rsvp/', views.rsvp_list, name='rsvp_list'),
    path('guest-wishes/', views.guest_wishes_list, name='guest_wishes_list'),
    path('checkins/', views.checkin_list, name='checkin_list'),
    path('whatsapp-logs/', views.whatsapp_log_list, name='whatsapp_log_list'),
    path('broadcasts/', views.broadcast_schedule_list, name='broadcast_schedule_list'),
    path('envelopes/', views.digital_envelope_list, name='digital_envelope_list'),
    path('feedback/', views.guest_feedback_list, name='guest_feedback_list'),
    
    # ===== AJAX ENDPOINTS =====
    path('ajax/bulk-action/', views.bulk_action, name='bulk_action'),
    path('ajax/export-data/', views.export_data, name='export_data'),
    path('ajax/notifications/<int:pk>/read/', views.mark_notification_read, name='mark_notification_read'),
    
    # ===== FUTURE EXTENSIONS (commented for now) =====
    # # Category Management
    # path('categories/', views.category_list, name='category_list'),
    # path('categories/add/', views.category_manage, name='category_add'),
    # path('categories/edit/<int:pk>/', views.category_manage, name='category_edit'),
    
    # # Package Management
    # path('packages/', views.package_list, name='package_list'),
    # path('packages/add/', views.package_manage, name='package_add'),
    # path('packages/edit/<int:pk>/', views.package_manage, name='package_edit'),
    
    # # Coupon Management
    # path('coupons/', views.coupon_list, name='coupon_list'),
    # path('coupons/add/', views.coupon_manage, name='coupon_add'),
    # path('coupons/edit/<int:pk>/', views.coupon_manage, name='coupon_edit'),
    
    # # Reports & Analytics
    # path('reports/', views.reports_dashboard, name='reports_dashboard'),
    # path('reports/revenue/', views.revenue_report, name='revenue_report'),
    # path('reports/users/', views.user_report, name='user_report'),
    # path('reports/themes/', views.theme_report, name='theme_report'),
    
    # # Settings
    # path('settings/', views.admin_settings, name='admin_settings'),
    # path('settings/notifications/', views.notification_settings, name='notification_settings'),
    # path('settings/email/', views.email_settings, name='email_settings'),
    
    # # Activity Logs
    # path('logs/', views.activity_log_list, name='activity_log_list'),
    # path('logs/<int:pk>/', views.activity_log_detail, name='activity_log_detail'),
]
