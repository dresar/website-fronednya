from django.urls import path
from . import views

app_name = 'public'

urlpatterns = [
    # Home page
    path('', views.home, name='home'),
    # Theme preview dan static files di-handle di invywed/urls.py untuk root level
]

