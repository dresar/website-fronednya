from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, Http404, JsonResponse
from django.conf import settings
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.urls import reverse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from pathlib import Path
import os
import logging
import re
import json
import shutil
from datetime import datetime
from django.utils.text import slugify

from .models import Category
from users.models import ClientProfile, Invitation, GroomInfo, BrideInfo, MainEvent, ReceptionEvent, PhotoGallery, LoveStory
from qr_manager.models import Guest

logger = logging.getLogger(__name__)


# Template variables for validation
TEMPLATE_VARIABLES = {
    'groom': {
        'name': 'groom',
        'type': 'Dictionary',
        'description': 'Informasi lengkap mempelai pria (dictionary)',
        'fields': [
            'groom.full_name', 'groom.nickname', 'groom.father_name',
            'groom.mother_name', 'groom.child_order', 'groom.main_photo'
        ],
        'example': '{{ groom.full_name }} atau {{ groom.nickname }}'
    },
    'bride': {
        'name': 'bride',
        'type': 'Dictionary',
        'description': 'Informasi lengkap mempelai wanita (dictionary)',
        'fields': [
            'bride.full_name', 'bride.nickname', 'bride.father_name',
            'bride.mother_name', 'bride.child_order', 'bride.main_photo'
        ],
        'example': '{{ bride.full_name }} atau {{ bride.nickname }}'
    },
    'event': {
        'name': 'event',
        'type': 'Dictionary dengan sub-keys',
        'description': 'Informasi acara pernikahan (mengandung akad dan reception)',
        'fields': [
            'event.akad.event_name', 'event.akad.event_date', 'event.akad.start_time',
            'event.akad.end_time', 'event.akad.venue_name', 'event.akad.venue_address',
            'event.akad.google_maps_url', 'event.reception.event_name', 'event.reception.event_date',
            'event.reception.venue_name'
        ],
        'example': '{{ event.akad.venue_name }} atau {% if event.reception %}{{ event.reception.venue_name }}{% endif %}'
    },
    'photo_gallery': {
        'name': 'photo_gallery',
        'type': 'QuerySet',
        'description': 'Galeri foto pasangan (QuerySet, bisa di-loop)',
        'fields': ['photo.image', 'photo.caption', 'photo.order'],
        'example': '{% for photo in photo_gallery %}<img src="{{ photo.image.url }}" alt="{{ photo.caption }}">{% endfor %}'
    },
    'love_stories': {
        'name': 'love_stories',
        'type': 'QuerySet',
        'description': 'Kisah cinta pasangan (QuerySet, bisa di-loop)',
        'fields': ['story.title', 'story.date', 'story.description', 'story.image'],
        'example': '{% for story in love_stories %}<div>{{ story.title }} - {{ story.date }}</div>{% endfor %}'
    },
    'guest_name': {
        'name': 'guest_name',
        'type': 'String',
        'description': 'Nama tamu yang mengakses undangan (hanya tersedia jika ada guest_slug)',
        'fields': ['guest_name'],
        'example': '{{ guest_name }}'
    },

}


def validate_django_template(html_content):
    """Validate Django template variables in HTML content"""
    errors = []
    warnings = []
    variables = []
    
    # Find all Django template variables {{ variable }} and {% tags %}
    var_pattern = r'\{\{\s*([^}]+)\s*\}\}'
    tag_pattern = r'\{\%\s*([^%]+)\s*\%\}'
    
    found_vars = re.findall(var_pattern, html_content)
    found_tags = re.findall(tag_pattern, html_content)
    
    # Extract variable names
    all_valid_vars = set()
    for var_info in TEMPLATE_VARIABLES.values():
        for field in var_info['fields']:
            all_valid_vars.add(field.split()[0])  # Get base variable name
    
    # Check variables
    for var_match in found_vars:
        var_match = var_match.strip()
        # Extract base variable (before . or |)
        base_var = var_match.split('.')[0].split('|')[0].strip()
        
        if base_var not in all_valid_vars and base_var not in ['guest_name']:
            warnings.append(f"Unknown variable: {var_match}")
        else:
            if var_match not in variables:
                variables.append(var_match)
    
    # Basic syntax check for tags
    open_tags = re.findall(r'\{\%\s*(if|for|block|extends|include)\s+', html_content)
    close_tags = re.findall(r'\{\%\s*end(if|for|block)\s*\%\}', html_content)
    
    if len(open_tags) != len(close_tags):
        errors.append("Mismatched Django template tags (if/for/block)")
    
    return {
        'errors': errors,
        'warnings': warnings,
        'variables': variables,
    }


@login_required
def template_editor_list(request):
    """List semua templates untuk dipilih di editor - REMOVED (Theme model deleted)"""
    messages.error(request, 'Template editor telah dinonaktifkan karena model Theme telah dihapus.')
    return redirect('admin_panel:dashboard')


@login_required
def template_editor_create(request):
    """Create new template - upload form - REMOVED (Theme model deleted)"""
    messages.error(request, 'Template editor telah dinonaktifkan karena model Theme telah dihapus.')
    return redirect('admin_panel:dashboard')



@login_required
def template_editor(request, slug):
    """Template editor - REMOVED (Theme model deleted)"""
    messages.error(request, 'Template editor telah dinonaktifkan karena model Theme telah dihapus.')
    return redirect('admin_panel:dashboard')


@login_required
def template_editor_docs(request, slug):
    """Documentation - REMOVED (Theme model deleted)"""
    messages.error(request, 'Template editor telah dinonaktifkan karena model Theme telah dihapus.')
    return redirect('admin_panel:dashboard')


@login_required
def preview_invitation(request, slug):
    """Preview invitation - REMOVED (Theme model deleted)"""
    messages.error(request, 'Preview invitation telah dinonaktifkan karena model Theme telah dihapus.')
    return redirect('admin_panel:dashboard')


def render_invitation(request, invitation_slug, guest_slug=None):
    """Render invitation - REMOVED (Theme model deleted)"""
    raise Http404('Template tidak ditemukan untuk undangan ini. Theme model telah dihapus.')


@require_POST
@csrf_exempt
def submit_wish(request, invitation_slug):
    """Submit wish/ucapan via AJAX (no reload)"""
    try:
        logger.info(f"Submit wish request for invitation_slug: {invitation_slug}")
        logger.info(f"Request method: {request.method}")
        logger.info(f"POST data: {request.POST}")
        logger.info(f"FILES data: {request.FILES}")
        
        invitation = Invitation.objects.get(invitation_slug=invitation_slug)
        logger.info(f"Invitation found: {invitation}")
    except Invitation.DoesNotExist:
        logger.error(f"Invitation not found: {invitation_slug}")
        return JsonResponse({
            'status': 'error',
            'message': 'Undangan tidak ditemukan.'
        }, status=404)
    except Exception as e:
        logger.error(f"Error getting invitation: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': f'Error: {str(e)}'
        }, status=500)
    
    # Get form data
    name = request.POST.get('name', '').strip()
    address = request.POST.get('alamat', '').strip()
    comment = request.POST.get('comment', '').strip()
    image = request.FILES.get('image', None)
    
    logger.info(f"Form data - name: {name}, address: {address}, comment length: {len(comment)}, has image: {image is not None}")
    
    # Validation
    if not name or not comment:
        logger.warning(f"Validation failed - name: {bool(name)}, comment: {bool(comment)}")
        return JsonResponse({
            'status': 'error',
            'message': 'Nama dan ucapan wajib diisi.'
        }, status=400)
    
    # Get IP address
    ip_address = None
    if 'HTTP_X_FORWARDED_FOR' in request.META:
        ip_address = request.META['HTTP_X_FORWARDED_FOR'].split(',')[0].strip()
    elif 'REMOTE_ADDR' in request.META:
        ip_address = request.META['REMOTE_ADDR']
    
    try:
        # Create InvitationWish
        from users.models import InvitationWish
        wish = InvitationWish.objects.create(
            invitation=invitation,
            name=name,
            address=address,
            comment=comment,
            image=image,
            ip_address=ip_address,
            is_approved=True  # Auto-approve for now
        )
        logger.info(f"Wish created successfully: {wish.id}")
        
        # Return success response with wish data
        return JsonResponse({
            'status': 'success',
            'message': 'Ucapan berhasil dikirim!',
            'wish': {
                'name': wish.name,
                'address': wish.address,
                'comment': wish.comment,
                'image': wish.image.url if wish.image else None,
                'submitted_at': wish.submitted_at.strftime('%d %b %Y, %H:%M'),
            }
        })
    except Exception as e:
        logger.error(f"Error creating wish: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return JsonResponse({
            'status': 'error',
            'message': f'Error menyimpan ucapan: {str(e)}'
        }, status=500)

