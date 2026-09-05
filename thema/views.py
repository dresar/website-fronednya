from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, Http404, JsonResponse, FileResponse
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.views.decorators.http import require_POST
from django.conf import settings
from django.utils.text import slugify
from django.db.models import Q
import os
import zipfile
import shutil
from pathlib import Path
import logging
import mimetypes
import re

from .models import Theme, ThemeCategory
from .forms import ThemeForm, ThemeCategoryForm

logger = logging.getLogger(__name__)


def extract_zip_to_template(zip_file, theme_slug):
    """
    Extract ZIP file ke folder templates/thema/nama-templates/
    Returns: path ke folder template yang diextract
    """
    try:
        # Base path untuk templates
        base_template_path = Path(settings.BASE_DIR) / 'templates' / 'thema'
        base_template_path.mkdir(parents=True, exist_ok=True)
        
        # Path untuk tema spesifik
        theme_template_path = base_template_path / theme_slug
        theme_template_path.mkdir(parents=True, exist_ok=True)
        
        # Extract ZIP
        with zipfile.ZipFile(zip_file, 'r') as zip_ref:
            zip_ref.extractall(theme_template_path)
        
        # Return relative path dari templates/
        return f"thema/{theme_slug}"
    
    except Exception as e:
        logger.error(f"Error extracting ZIP: {str(e)}")
        raise ValidationError(f"Error extracting ZIP file: {str(e)}")


def validate_zip_content(zip_file):
    """
    Validasi bahwa ZIP file berisi file HTML utama (index.html atau main.html)
    Returns: (is_valid, main_html_file)
    """
    try:
        with zipfile.ZipFile(zip_file, 'r') as zip_ref:
            file_list = zip_ref.namelist()
            
            # Cari file HTML utama
            html_files = [f for f in file_list if f.endswith('.html')]
            
            # Cek index.html atau main.html
            main_html = None
            for html_file in html_files:
                filename = os.path.basename(html_file)
                if filename.lower() in ['index.html', 'main.html', 'template.html']:
                    main_html = html_file
                    break
            
            # Jika tidak ada, ambil HTML pertama
            if not main_html and html_files:
                main_html = html_files[0]
            
            if not main_html:
                return False, None
            
            return True, main_html
    
    except Exception as e:
        logger.error(f"Error validating ZIP: {str(e)}")
        return False, None


# ===== PUBLIC VIEWS =====

def themes_filter_ajax(request):
    """AJAX endpoint untuk filter themes berdasarkan kategori"""
    try:
        category_slug = request.GET.get('category', 'all')
        
        # Get themes
        themes_query = Theme.objects.filter(is_active=True).select_related('category')
        
        # Filter by category
        if category_slug != 'all':
            themes_query = themes_query.filter(category__slug=category_slug)
        
        themes = themes_query.order_by('-created_at')  # Get all themes for theme list page
        
        # Serialize themes
        themes_data = []
        for theme in themes:
            themes_data.append({
                'id': theme.id,
                'name': theme.name,
                'slug': theme.slug,
                'thumbnail_url': theme.thumbnail.url if theme.thumbnail else '',
                'category_slug': theme.category.slug if theme.category else 'all',
                'demo_url': f'/demo/{theme.slug}/',
            })
        
        return JsonResponse({
            'status': 'success',
            'themes': themes_data,
            'count': len(themes_data)
        })
    except Exception as e:
        logger.error(f"Error filtering themes: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': f'Error: {str(e)}'
        }, status=500)


def theme_static(request, slug, file_path):
    """
    Serve static files (CSS, JS, images, etc.) from templates/thema/{slug}/ folder
    """
    # Get theme to verify it exists and is active
    try:
        theme = Theme.objects.get(slug=slug, is_active=True)
    except Theme.DoesNotExist:
        raise Http404('Theme not found')
    
    # Get template path
    template_path = theme.get_template_path()
    if not template_path:
        raise Http404("Template tidak ditemukan")
    
    # Build file path
    base_dir = Path(settings.BASE_DIR)
    theme_base_path = base_dir / 'templates' / template_path
    file_path_obj = theme_base_path / file_path
    
    # Security: prevent directory traversal
    try:
        file_path_obj.resolve().relative_to(theme_base_path.resolve())
    except ValueError:
        raise Http404('Invalid path')
    
    # Check if file exists
    if not file_path_obj.exists() or not file_path_obj.is_file():
        raise Http404('File not found')
    
    # Determine MIME type
    mime_type, _ = mimetypes.guess_type(str(file_path_obj))
    if not mime_type:
        # Default MIME types for common extensions
        ext = file_path_obj.suffix.lower()
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
            '.mp4': 'video/mp4',
            '.pdf': 'application/pdf',
        }
        mime_type = mime_types.get(ext, 'application/octet-stream')
    
    # Serve file
    try:
        response = FileResponse(open(file_path_obj, 'rb'), content_type=mime_type)
        # Add cache headers
        response['Cache-Control'] = 'public, max-age=3600'  # 1 hour
        return response
    except Exception as e:
        logger.error(f"Error serving theme static file: {str(e)}")
        raise Http404('Error serving file')


def theme_demo(request, slug):
    """Public demo view untuk preview tema"""
    theme = get_object_or_404(Theme, slug=slug, is_active=True)
    
    # Increment view count
    theme.view_count += 1
    theme.save(update_fields=['view_count'])
    
    # Get template path
    template_path = theme.get_template_path()
    if not template_path:
        raise Http404("Template tidak ditemukan")
    
    # Path ke folder template
    full_template_path = Path(settings.BASE_DIR) / 'templates' / template_path
    
    # Cari file HTML utama
    html_files = ['index.html', 'main.html', 'template.html']
    main_html = None
    
    for html_file in html_files:
        html_path = full_template_path / html_file
        if html_path.exists():
            main_html = html_file
            break
    
    # Jika tidak ada, cari HTML file pertama
    if not main_html:
        for file_path in full_template_path.rglob('*.html'):
            main_html = file_path.relative_to(full_template_path)
            break
    
    if not main_html:
        raise Http404("File HTML tidak ditemukan di template")
    
    # Read HTML content
    html_path = full_template_path / main_html
    with open(html_path, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    # Fix relative paths in HTML content
    # Replace relative paths (css/style.css) with /demo/<slug>/css/style.css
    # But keep absolute paths (/static/, /media/, http://) unchanged
    base_url = f'/demo/{slug}/'
    
    # Fix CSS links: href="css/style.css" -> href="/demo/weed/css/style.css"
    html_content = re.sub(
        r'(<link[^>]+href=["\'])(?!https?://|//|/static/|/media/|/demo/)([^"\']+)(["\'])',
        lambda m: f'{m.group(1)}{base_url}{m.group(2)}{m.group(3)}',
        html_content,
        flags=re.IGNORECASE
    )
    
    # Fix JS scripts: src="js/script.js" -> src="/demo/weed/js/script.js"
    html_content = re.sub(
        r'(<script[^>]+src=["\'])(?!https?://|//|/static/|/media/|/demo/)([^"\']+)(["\'])',
        lambda m: f'{m.group(1)}{base_url}{m.group(2)}{m.group(3)}',
        html_content,
        flags=re.IGNORECASE
    )
    
    # Fix images: src="images/img.jpg" -> src="/demo/weed/images/img.jpg"
    html_content = re.sub(
        r'(<img[^>]+src=["\'])(?!https?://|//|/static/|/media/|/demo/)([^"\']+)(["\'])',
        lambda m: f'{m.group(1)}{base_url}{m.group(2)}{m.group(3)}',
        html_content,
        flags=re.IGNORECASE
    )
    
    # Fix absolute paths that start with / but not /static/, /media/, or /demo/
    # e.g., /css/style.css -> /demo/weed/css/style.css
    html_content = re.sub(
        r'(href|src)=["\'](?!https?://|//|/static/|/media/|/demo/)(/[^"\']+)["\']',
        lambda m: f'{m.group(1)}="{base_url}{m.group(2)[1:]}"',  # Remove leading / from m.group(2)
        html_content,
        flags=re.IGNORECASE
    )
    
    # Return HTML content directly without wrapper template
    return HttpResponse(html_content, content_type='text/html; charset=utf-8')


# ===== ADMIN VIEWS =====

@login_required
@user_passes_test(lambda u: u.is_staff or u.is_superuser)
def theme_list(request):
    """List semua tema di admin panel"""
    themes = Theme.objects.select_related('category').all()
    
    # Filters
    search = request.GET.get('search', '')
    category_filter = request.GET.get('category', '')
    status_filter = request.GET.get('status', '')
    
    if search:
        themes = themes.filter(
            Q(name__icontains=search) |
            Q(description__icontains=search) |
            Q(slug__icontains=search)
        )
    
    if category_filter:
        themes = themes.filter(category_id=category_filter)
    
    if status_filter == 'active':
        themes = themes.filter(is_active=True)
    elif status_filter == 'inactive':
        themes = themes.filter(is_active=False)
    
    categories = ThemeCategory.objects.filter(is_active=True)
    
    context = {
        'themes': themes.order_by('-created_at'),
        'categories': categories,
        'current_search': search,
        'current_category': category_filter,
        'current_status': status_filter,
    }
    
    return render(request, 'admin_panel/thema/theme_list.html', context)


@login_required
@user_passes_test(lambda u: u.is_staff or u.is_superuser)
def theme_upload(request):
    """Upload tema baru"""
    if request.method == 'POST':
        form = ThemeForm(request.POST, request.FILES)
        if form.is_valid():
            theme = form.save(commit=False)
            
            # Generate slug
            if not theme.slug:
                theme.slug = slugify(theme.name)
            
            # Validate ZIP
            zip_file = form.cleaned_data['zip_file']
            is_valid, main_html = validate_zip_content(zip_file)
            
            if not is_valid:
                messages.error(request, 'ZIP file harus berisi minimal satu file HTML (index.html, main.html, atau template.html)')
                return render(request, 'admin_panel/thema/theme_form.html', {'form': form})
            
            # Extract ZIP first (before saving theme)
            try:
                extracted_path = extract_zip_to_template(zip_file, theme.slug)
            except Exception as e:
                messages.error(request, f'Error extracting ZIP: {str(e)}')
                return render(request, 'admin_panel/thema/theme_form.html', {'form': form, 'title': 'Upload Tema Baru'})
            
            # Set extracted path before saving
            theme.extracted_path = extracted_path
            
            # Save theme after successful extraction
            theme.save()
            
            messages.success(request, f'Tema "{theme.name}" berhasil diupload dan diextract!')
            return redirect('admin_panel:theme_list')
    else:
        form = ThemeForm()
    
    context = {
        'form': form,
        'title': 'Upload Tema Baru',
    }
    
    return render(request, 'admin_panel/thema/theme_form.html', context)


@login_required
@user_passes_test(lambda u: u.is_staff or u.is_superuser)
def theme_edit(request, pk):
    """Edit tema"""
    theme = get_object_or_404(Theme, pk=pk)
    
    if request.method == 'POST':
        form = ThemeForm(request.POST, request.FILES, instance=theme)
        if form.is_valid():
            # Jika ZIP file baru diupload
            if 'zip_file' in request.FILES:
                zip_file = form.cleaned_data['zip_file']
                is_valid, main_html = validate_zip_content(zip_file)
                
                if not is_valid:
                    messages.error(request, 'ZIP file harus berisi minimal satu file HTML')
                    return render(request, 'admin_panel/thema/theme_form.html', {'form': form, 'theme': theme, 'title': f'Edit Tema: {theme.name}'})
                
                # Hapus folder template lama
                if theme.extracted_path:
                    old_path = Path(settings.BASE_DIR) / 'templates' / theme.extracted_path
                    if old_path.exists():
                        shutil.rmtree(old_path)
                
                # Extract ZIP baru (before saving)
                try:
                    extracted_path = extract_zip_to_template(zip_file, theme.slug)
                except Exception as e:
                    messages.error(request, f'Error extracting ZIP: {str(e)}')
                    return render(request, 'admin_panel/thema/theme_form.html', {'form': form, 'theme': theme, 'title': f'Edit Tema: {theme.name}'})
                
                # Update extracted path after successful extraction
                # Set pada form instance sebelum save
                form.instance.extracted_path = extracted_path
            
            # Save theme (will include extracted_path if ZIP was uploaded)
            theme = form.save()
            
            messages.success(request, f'Tema "{theme.name}" berhasil diupdate!')
            return redirect('admin_panel:theme_list')
    else:
        form = ThemeForm(instance=theme)
    
    context = {
        'form': form,
        'theme': theme,
        'title': f'Edit Tema: {theme.name}',
    }
    
    return render(request, 'admin_panel/thema/theme_form.html', context)


@login_required
@user_passes_test(lambda u: u.is_staff or u.is_superuser)
@require_POST
def theme_delete(request, pk):
    """Delete tema"""
    theme = get_object_or_404(Theme, pk=pk)
    theme_name = theme.name
    
    # Hapus folder template
    if theme.extracted_path:
        template_path = Path(settings.BASE_DIR) / 'templates' / theme.extracted_path
        if template_path.exists():
            shutil.rmtree(template_path)
    
    # Hapus ZIP file
    if theme.zip_file:
        theme.zip_file.delete()
    
    # Hapus thumbnail
    if theme.thumbnail:
        theme.thumbnail.delete()
    
    # Delete theme
    theme.delete()
    
    messages.success(request, f'Tema "{theme_name}" berhasil dihapus!')
    return redirect('admin_panel:theme_list')


@login_required
@user_passes_test(lambda u: u.is_staff or u.is_superuser)
def theme_download(request, pk):
    """Download ZIP file tema"""
    theme = get_object_or_404(Theme, pk=pk)
    
    if not theme.zip_file:
        messages.error(request, 'File ZIP tidak ditemukan')
        return redirect('admin_panel:theme_list')
    
    # Increment download count
    theme.download_count += 1
    theme.save(update_fields=['download_count'])
    
    # Return file response
    response = FileResponse(theme.zip_file.open('rb'), content_type='application/zip')
    response['Content-Disposition'] = f'attachment; filename="{theme.slug}.zip"'
    
    return response


@login_required
@user_passes_test(lambda u: u.is_staff or u.is_superuser)
def theme_preview(request, pk):
    """Preview tema di admin panel"""
    theme = get_object_or_404(Theme, pk=pk)
    return redirect(f'/demo/{theme.slug}/')


# ===== CATEGORY MANAGEMENT VIEWS =====

@login_required
@user_passes_test(lambda u: u.is_staff or u.is_superuser)
@require_POST
def category_create(request):
    """Create kategori baru via AJAX"""
    from django.http import JsonResponse
    
    try:
        form = ThemeCategoryForm(request.POST)
        if form.is_valid():
            category = form.save()
            return JsonResponse({
                'status': 'success',
                'message': f'Kategori "{category.name}" berhasil dibuat!',
                'category': {
                    'id': category.id,
                    'name': category.name,
                    'slug': category.slug,
                }
            })
        else:
            return JsonResponse({
                'status': 'error',
                'message': 'Validasi gagal',
                'errors': form.errors
            }, status=400)
    except Exception as e:
        logger.error(f"Error creating category: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': f'Error: {str(e)}'
        }, status=500)


@login_required
@user_passes_test(lambda u: u.is_staff or u.is_superuser)
@require_POST
def category_update(request, pk):
    """Update kategori via AJAX"""
    from django.http import JsonResponse
    
    try:
        category = get_object_or_404(ThemeCategory, pk=pk)
        form = ThemeCategoryForm(request.POST, instance=category)
        if form.is_valid():
            category = form.save()
            return JsonResponse({
                'status': 'success',
                'message': f'Kategori "{category.name}" berhasil diupdate!',
                'category': {
                    'id': category.id,
                    'name': category.name,
                    'slug': category.slug,
                }
            })
        else:
            return JsonResponse({
                'status': 'error',
                'message': 'Validasi gagal',
                'errors': form.errors
            }, status=400)
    except Exception as e:
        logger.error(f"Error updating category: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': f'Error: {str(e)}'
        }, status=500)


@login_required
@user_passes_test(lambda u: u.is_staff or u.is_superuser)
@require_POST
def category_delete(request, pk):
    """Delete kategori via AJAX"""
    from django.http import JsonResponse
    
    try:
        category = get_object_or_404(ThemeCategory, pk=pk)
        category_name = category.name
        
        # Cek apakah ada theme yang menggunakan kategori ini
        theme_count = Theme.objects.filter(category=category).count()
        if theme_count > 0:
            return JsonResponse({
                'status': 'error',
                'message': f'Tidak dapat menghapus kategori karena masih digunakan oleh {theme_count} tema. Hapus atau pindahkan tema terlebih dahulu.'
            }, status=400)
        
        category.delete()
        return JsonResponse({
            'status': 'success',
            'message': f'Kategori "{category_name}" berhasil dihapus!'
        })
    except Exception as e:
        logger.error(f"Error deleting category: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': f'Error: {str(e)}'
        }, status=500)


@login_required
@user_passes_test(lambda u: u.is_staff or u.is_superuser)
def category_list_ajax(request):
    """Get list kategori untuk dropdown via AJAX"""
    from django.http import JsonResponse
    
    try:
        # Get all categories (not just active) for management
        include_inactive = request.GET.get('include_inactive', 'false').lower() == 'true'
        
        if include_inactive:
            categories = ThemeCategory.objects.all().order_by('order', 'name')
        else:
            categories = ThemeCategory.objects.filter(is_active=True).order_by('order', 'name')
        
        categories_data = [{
            'id': cat.id,
            'name': cat.name,
            'slug': cat.slug,
            'is_active': cat.is_active,
        } for cat in categories]
        
        return JsonResponse({
            'status': 'success',
            'categories': categories_data
        })
    except Exception as e:
        logger.error(f"Error getting categories: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': f'Error: {str(e)}'
        }, status=500)


@login_required
@user_passes_test(lambda u: u.is_staff or u.is_superuser)
def category_get(request, pk):
    """Get detail kategori via AJAX"""
    from django.http import JsonResponse
    
    try:
        category = get_object_or_404(ThemeCategory, pk=pk)
        return JsonResponse({
            'status': 'success',
            'category': {
                'id': category.id,
                'name': category.name,
                'slug': category.slug,
                'description': category.description,
                'icon_class': category.icon_class,
                'order': category.order,
                'is_active': category.is_active,
            }
        })
    except Exception as e:
        logger.error(f"Error getting category: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': f'Error: {str(e)}'
        }, status=500)
