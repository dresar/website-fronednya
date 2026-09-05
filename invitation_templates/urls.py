from django.urls import path, re_path
from . import views

app_name = 'invitation_templates'

urlpatterns = [
    # Template editor list - accessed via /editor/
    path('', views.template_editor_list, name='template_editor_list'),
    # Template create - accessed via /editor/create/
    path('create/', views.template_editor_create, name='template_editor_create'),
    # Editor documentation/tutorial - accessed via /editor/<slug>/docs/
    path('<slug:slug>/docs/', views.template_editor_docs, name='template_editor_docs'),
    # Template editor - accessed via /editor/<slug>/ (edit only)
    path('<slug:slug>/', views.template_editor, name='template_editor'),
    # Theme preview public sudah dipindahkan ke core/views.py
    # URL sekarang: /demo/<slug>/ (handled in invywed/urls.py)
]

