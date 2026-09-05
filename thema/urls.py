from django.urls import path, re_path
from . import views

app_name = 'thema'

# Public demo URLs - accessed via /demo/<slug>/
# IMPORTANT: Static files pattern must come BEFORE the slug pattern
# to catch requests like /demo/weed/css/style.css
urlpatterns = [
    # Serve static files (CSS, JS, images, etc.) - must be first
    # This pattern matches paths that have additional path segments after the slug
    # e.g., /demo/weed/css/style.css, /demo/weed/js/script.js
    re_path(r'^(?P<slug>[\w-]+)/(?P<file_path>.+)$', views.theme_static, name='theme_static'),
    # Demo page - matches only /demo/<slug>/ (with trailing slash)
    path('<slug:slug>/', views.theme_demo, name='theme_demo'),
    # Also match /demo/<slug> without trailing slash
    path('<slug:slug>', views.theme_demo, name='theme_demo_no_slash'),
]
