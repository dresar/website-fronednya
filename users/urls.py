from django.urls import path
from . import views

app_name = 'users'

urlpatterns = [
    # ===== AUTHENTICATION =====
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('register/', views.user_register, name='register'),
    
    # ===== DASHBOARD =====
    path('dashboard/', views.dashboard, name='dashboard'),
    
    # ===== WEDDING DATA FORM =====
    path('wedding-data/', views.wedding_data_form, name='wedding_data_form'),
    
    # ===== GUEST MANAGEMENT =====
    path('guests/', views.guest_manager, name='guest_manager'),
    path('guests/add/', views.add_guest, name='add_guest'),
    path('guests/<int:pk>/edit/', views.edit_guest, name='edit_guest'),
    path('guests/<int:pk>/delete/', views.delete_guest, name='delete_guest'),
    
    # ===== RSVP FEED =====
    path('rsvp-feed/', views.rsvp_feed, name='rsvp_feed'),
    
    # ===== PROFILE =====
    path('profile/', views.profile, name='profile'),
    path('profile/select-theme/', views.select_theme, name='select_theme'),
    path('profile/search-themes/', views.search_themes, name='search_themes'),
    path('profile/change-password/', views.change_password, name='change_password'),
    path('profile/notifications/', views.notifications, name='notifications'),
    path('profile/help/', views.help, name='help'),
]

