from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, Http404, FileResponse
from django.conf import settings
from django.template import Template, RequestContext, Engine
from invitation_templates.models import Category
from django.db.models import Q
from pathlib import Path
import re
import logging
import mimetypes
import os
import traceback

logger = logging.getLogger(__name__)

# Create your views here.

def home(request):
    """Home page"""
    # Get themes from thema app
    try:
        from thema.models import Theme, ThemeCategory
        themes = Theme.objects.filter(is_active=True).select_related('category').order_by('-created_at')[:12]
        categories = ThemeCategory.objects.filter(is_active=True).order_by('order', 'name')
    except ImportError:
        themes = []
        categories = []
    
    # Get WhatsApp templates and FAQ
    try:
        from qr_manager.models import WhatsAppUserTemplate, WhatsAppNumber
        whatsapp_templates = WhatsAppUserTemplate.objects.filter(is_active=True).order_by('template_type', 'template_name')
        whatsapp_number = WhatsAppNumber.objects.filter(is_default=True).first()
        if not whatsapp_number:
            whatsapp_number = WhatsAppNumber.objects.filter(is_active=True).first()
    except ImportError:
        whatsapp_templates = []
        whatsapp_number = None
    
    try:
        from core.models import FaqItem
        faq_items = FaqItem.objects.filter(is_active=True).order_by('category', 'order')[:10]
    except ImportError:
        faq_items = []
    
    # Get total stats (dummy data untuk sekarang, bisa diganti dengan real data)
    context = {
        'total_active_invitations': 47391,  # Placeholder
        'total_gifts': 9163,  # Placeholder
        'total_wishes': 835339,  # Placeholder
        'total_rsvp': 763563,  # Placeholder
        'themes': themes,
        'categories': categories,
        'whatsapp_templates': whatsapp_templates,
        'whatsapp_number': whatsapp_number,
        'faq_items': faq_items,
    }
    
    return render(request, 'public/home.html', context)


def theme_list(request):
    """Public theme list page - All themes"""
    # Get all active themes and categories
    try:
        from thema.models import Theme, ThemeCategory
        themes = Theme.objects.filter(is_active=True).select_related('category').order_by('-created_at')
        categories = ThemeCategory.objects.filter(is_active=True).order_by('order', 'name')
    except ImportError:
        themes = []
        categories = []
    
    context = {
        'themes': themes,
        'categories': categories,
    }
    
    return render(request, 'public/theme_list.html', context)


def _theme_preview_public_removed(request, slug):
    """Public preview HTML template file using slug (no login required) - Moved to core"""
    theme = get_object_or_404(PublicTheme, slug=slug, is_active=True)
    
    if not theme.html_file:
        # Return error page instead of raising Http404
        error_html = """
        <!DOCTYPE html>
        <html lang="id">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Template Tidak Ditemukan</title>
            <style>
                body {
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    min-height: 100vh;
                    margin: 0;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                }
                .error-container {
                    background: white;
                    padding: 3rem;
                    border-radius: 1rem;
                    box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1);
                    text-align: center;
                    max-width: 500px;
                }
                .error-icon {
                    font-size: 4rem;
                    color: #ef4444;
                    margin-bottom: 1rem;
                }
                h1 {
                    color: #1f2937;
                    margin-bottom: 1rem;
                }
                p {
                    color: #6b7280;
                    line-height: 1.6;
                }
            </style>
        </head>
        <body>
            <div class="error-container">
                <div class="error-icon">⚠️</div>
                <h1>Template Tidak Ditemukan</h1>
                <p>File HTML untuk template "<strong>{}</strong>" tidak ditemukan atau belum diupload.</p>
                <p style="margin-top: 1rem; font-size: 0.875rem;">Silakan hubungi administrator untuk memperbaiki masalah ini.</p>
            </div>
        </body>
        </html>
        """.format(theme.name)
        return HttpResponse(error_html, content_type='text/html; charset=utf-8', status=404)
    
    # Get file path from templates_html folder in media
    file_path = theme.get_template_path('index.html')
    
    if not file_path.exists():
        # Return error page instead of raising Http404
        error_html = """
        <!DOCTYPE html>
        <html lang="id">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Template Tidak Ditemukan</title>
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    min-height: 100vh;
                    margin: 0;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                }}
                .error-container {{
                    background: white;
                    padding: 3rem;
                    border-radius: 1rem;
                    box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1);
                    text-align: center;
                    max-width: 500px;
                }}
                .error-icon {{
                    font-size: 4rem;
                    color: #ef4444;
                    margin-bottom: 1rem;
                }}
                h1 {{
                    color: #1f2937;
                    margin-bottom: 1rem;
                }}
                p {{
                    color: #6b7280;
                    line-height: 1.6;
                }}
            </style>
        </head>
        <body>
            <div class="error-container">
                <div class="error-icon">⚠️</div>
                <h1>Template Tidak Ditemukan</h1>
                <p>File HTML untuk template "<strong>{}</strong>" sudah hilang atau tidak ditemukan di server.</p>
                <p style="margin-top: 1rem; font-size: 0.875rem;">File yang diharapkan: <code style="background: #f3f4f6; padding: 0.25rem 0.5rem; border-radius: 0.25rem;">{}</code></p>
                <p style="margin-top: 1rem; font-size: 0.875rem;">Silakan hubungi administrator untuk memperbaiki masalah ini.</p>
            </div>
        </body>
        </html>
        """.format(theme.name, theme.html_file)
        return HttpResponse(error_html, content_type='text/html; charset=utf-8', status=404)
    
    # Read HTML file and render as Django template
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        # Replace relative paths with absolute paths to /thema/<slug>/
        # This ensures CSS, JS, images, etc. are loaded correctly
        theme_base_url = f'/thema/{slug}/'
        
        # Replace relative paths in href and src attributes
        # Pattern: href="css/..." or src="images/..." or href="/css/..." (absolute from root)
        def replace_relative_path(match):
            attr = match.group(1)  # href or src
            quote = match.group(2)  # " or '
            path = match.group(3)
            # Skip if already has http/https or data: or javascript: or #
            if path.startswith('http') or path.startswith('data:') or path.startswith('javascript:') or path.startswith('#'):
                return match.group(0)
            # If path starts with /, remove it and use theme_base_url
            if path.startswith('/'):
                path = path[1:]  # Remove leading /
            # Make absolute path
            return f'{attr}={quote}{theme_base_url}{path}{quote}'
        
        # Replace in href and src attributes
        html_content = re.sub(r'(href|src)=(["\'])([^"\']+)\2', replace_relative_path, html_content)
        
        # Replace in CSS url() functions
        def replace_url_path(match):
            quote = match.group(1)  # " or ' or empty
            path = match.group(2)
            # Skip if already has http/https or data:
            if path.startswith('http') or path.startswith('data:'):
                return match.group(0)
            # If path starts with /, remove it
            if path.startswith('/'):
                path = path[1:]
            return f'url({quote}{theme_base_url}{path}{quote})'
        
        html_content = re.sub(r'url\((["\']?)([^"\')]+)\1\)', replace_url_path, html_content)
        
        # Get template wishes (default wishes for preview)
        template_wish = PublicThemeWish.objects.filter(theme=theme).first()
        wishes_list = template_wish.get_wishes_list() if template_wish else []
        
        # Build context for preview (with dummy data for preview)
        context = {
            'theme': theme,
            'groom': {
                'full_name': 'Eka',
                'nickname': 'Eka',
                'father_name': 'Tjipto Gunawan',
                'mother_name': 'Felicia Susanto',
                'child_order': 'Pertama',
                'main_photo': None,
            },
            'bride': {
                'full_name': 'Indah',
                'nickname': 'Indah',
                'father_name': 'Budiman Thamrin',
                'mother_name': 'Sarah Erawati',
                'child_order': 'Pertama',
                'main_photo': None,
            },
            'event': {
                'akad': {
                    'event_name': 'Acara Pernikahan',
                    'event_date': 'Minggu, 5 Mei 2025',
                    'start_time': '08:00',
                    'end_time': '10:00',
                    'venue_name': 'Hotel Shangri-La',
                    'venue_address': 'Jl. Jend. Sudirman No.Kav. 1',
                    'google_maps_url': '#',
                },
                'reception': None,
            },
            'photo_gallery': [],
            'love_stories': [],
            'guest_name': None,
            'guest': None,
            'wishes': wishes_list,  # Template wishes untuk preview
            'invitation_slug': None,  # Preview template tidak punya invitation_slug
            'is_preview': True,  # Flag untuk membedakan preview vs real invitation
        }
        
        # Create template engine with staticfiles
        engine = Engine.get_default()
        template = engine.from_string(html_content)
        rendered_html = template.render(RequestContext(request, context))
        
        return HttpResponse(rendered_html, content_type='text/html; charset=utf-8')
    except Exception as e:
        logger.error(f"Error reading/rendering template file: {str(e)}")
        error_traceback = traceback.format_exc()
        logger.error(error_traceback)
        # Return error page with detailed error information
        error_html = """
        <!DOCTYPE html>
        <html lang="id">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Error Membaca Template</title>
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    min-height: 100vh;
                    margin: 0;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    padding: 2rem;
                }}
                .error-container {{
                    background: white;
                    padding: 2rem;
                    border-radius: 1rem;
                    box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1);
                    max-width: 800px;
                    width: 100%;
                }}
                .error-icon {{
                    font-size: 4rem;
                    color: #ef4444;
                    margin-bottom: 1rem;
                    text-align: center;
                }}
                h1 {{
                    color: #1f2937;
                    margin-bottom: 1rem;
                    text-align: center;
                }}
                .error-details {{
                    background: #fef2f2;
                    border: 1px solid #fecaca;
                    border-radius: 0.5rem;
                    padding: 1rem;
                    margin-top: 1rem;
                }}
                .error-details h3 {{
                    color: #991b1b;
                    font-size: 1rem;
                    margin-bottom: 0.5rem;
                }}
                .error-message {{
                    color: #dc2626;
                    font-weight: 600;
                    margin-bottom: 0.5rem;
                }}
                .error-traceback {{
                    background: #1f2937;
                    color: #f3f4f6;
                    padding: 1rem;
                    border-radius: 0.5rem;
                    font-family: 'Courier New', monospace;
                    font-size: 0.75rem;
                    overflow-x: auto;
                    white-space: pre-wrap;
                    word-wrap: break-word;
                    max-height: 400px;
                    overflow-y: auto;
                    margin-top: 0.5rem;
                }}
                .error-info {{
                    background: #eff6ff;
                    border: 1px solid #bfdbfe;
                    border-radius: 0.5rem;
                    padding: 1rem;
                    margin-top: 1rem;
                }}
                .error-info h3 {{
                    color: #1e40af;
                    font-size: 1rem;
                    margin-bottom: 0.5rem;
                }}
                .error-info p {{
                    color: #1e3a8a;
                    margin: 0.25rem 0;
                    font-size: 0.875rem;
                }}
                .error-info code {{
                    background: #dbeafe;
                    padding: 0.125rem 0.25rem;
                    border-radius: 0.25rem;
                    font-size: 0.875rem;
                }}
            </style>
        </head>
        <body>
            <div class="error-container">
                <div class="error-icon">❌</div>
                <h1>Error Membaca Template</h1>
                <p style="text-align: center; color: #6b7280;">Terjadi kesalahan saat membaca/men-render file template "<strong>{}</strong>".</p>
                
                <div class="error-details">
                    <h3>Detail Error:</h3>
                    <div class="error-message">Type: {}</div>
                    <div class="error-message">Message: {}</div>
                </div>
                
                <div class="error-info">
                    <h3>Informasi Template:</h3>
                    <p><strong>Nama Template:</strong> {}</p>
                    <p><strong>Slug Template:</strong> {}</p>
                    <p><strong>File Path:</strong> <code>{}</code></p>
                    <p><strong>File Exists:</strong> {}</p>
                </div>
                
                <div class="error-details" style="margin-top: 1rem;">
                    <h3>Traceback (untuk debugging):</h3>
                    <div class="error-traceback">{}</div>
                </div>
                
                <p style="margin-top: 1.5rem; text-align: center; font-size: 0.875rem; color: #6b7280;">
                    Silakan hubungi administrator untuk memperbaiki masalah ini.
                </p>
            </div>
        </body>
        </html>
        """.format(
            theme.name,
            type(e).__name__,
            str(e),
            theme.name,
            theme.slug,
            file_path,
            'Ya' if file_path.exists() else 'Tidak',
            error_traceback.replace('<', '&lt;').replace('>', '&gt;')
        )
        return HttpResponse(error_html, content_type='text/html; charset=utf-8', status=500)


def _serve_theme_static_removed(request, slug, path):
    """Serve static files (CSS, JS, images, etc.) from thema/{slug}/ folder - Moved to core"""
    # Get theme to verify it exists
    try:
        theme = PublicTheme.objects.get(slug=slug, is_active=True)
    except PublicTheme.DoesNotExist:
        raise Http404('Theme not found')
    
    # Build file path
    base_dir = Path(settings.BASE_DIR)
    file_path = base_dir / 'thema' / slug / path
    
    # Security: prevent directory traversal
    try:
        file_path.resolve().relative_to((base_dir / 'thema' / slug).resolve())
    except ValueError:
        raise Http404('Invalid path')
    
    # Check if file exists
    if not file_path.exists() or not file_path.is_file():
        raise Http404('File not found')
    
    # Determine MIME type
    mime_type, _ = mimetypes.guess_type(str(file_path))
    if not mime_type:
        # Default MIME types for common extensions
        ext = file_path.suffix.lower()
        mime_types = {
            '.css': 'text/css',
            '.js': 'application/javascript',
            '.json': 'application/json',
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.gif': 'image/gif',
            '.svg': 'image/svg+xml',
            '.webp': 'image/webp',
            '.woff': 'font/woff',
            '.woff2': 'font/woff2',
            '.ttf': 'font/ttf',
            '.eot': 'application/vnd.ms-fontobject',
            '.mp3': 'audio/mpeg',
            '.mp4': 'video/mp4',
        }
        mime_type = mime_types.get(ext, 'application/octet-stream')
    
    # Serve file
    try:
        response = FileResponse(open(file_path, 'rb'), content_type=mime_type)
        # Add cache headers
        response['Cache-Control'] = 'public, max-age=31536000'  # 1 year
        return response
    except Exception as e:
        logger.error(f"Error serving theme static file: {str(e)}")
        raise Http404('Error serving file')
