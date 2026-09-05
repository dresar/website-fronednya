from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse, Http404
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Count, Q, Sum, Avg, F, Case, When, IntegerField
from django.db import transaction
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.core.exceptions import ValidationError, PermissionDenied
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_http_methods
from django.views.generic import TemplateView, ListView
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from django.urls import reverse
from datetime import timedelta, datetime
import json
import csv
import logging
import os
import zipfile
import shutil
from pathlib import Path

# Import models
from invitation_templates.models import (
    Category
)
from users.models import (
    ClientProfile, GroomInfo, BrideInfo, MainEvent, ReceptionEvent, Invitation
)
from core.models import (
    BlogPost, BlogCategory, 
    Testimonial, PricingPackage, PackageFeature, DiscountCoupon,
    PaymentMethod, RefundRequest, TicketReply, FaqItem,
    PartnerVendor, SiteConfiguration, MaintenanceLog
)
from qr_manager.models import (
    Guest, GuestGroup, InvitationCode, WhatsAppTemplate, WhatsAppLog,
    RSVPResponse, GuestWishes, CheckInLog, TableAssignment, SouvenirLog,
    GuestTag, ScanOperator, DigitalEnvelope, BroadcastSchedule, GuestFeedback,
    WhatsAppNumber, WhatsAppUserTemplate
)
from .models import ActivityLog

# Setup logging
logger = logging.getLogger(__name__)

# ===== BASE CONTROLLER & HELPERS =====

class BaseAdminController:
    """Base controller dengan utility functions untuk admin panel"""
    
    @staticmethod
    def get_pagination_context(request, queryset, items_per_page=25):
        """Handle pagination dengan error handling"""
        try:
            paginator = Paginator(queryset, items_per_page)
            page = request.GET.get('page')
            
            try:
                items = paginator.page(page)
            except PageNotAnInteger:
                items = paginator.page(1)
            except EmptyPage:
                items = paginator.page(paginator.num_pages)
                
            return {
                'items': items,
                'paginator': paginator,
                'page_obj': items,
                'is_paginated': paginator.num_pages > 1,
                'has_previous': items.has_previous(),
                'has_next': items.has_next(),
                'previous_page_number': items.previous_page_number() if items.has_previous() else None,
                'next_page_number': items.next_page_number() if items.has_next() else None,
            }
        except Exception as e:
            logger.error(f"Pagination error: {str(e)}")
            return {
                'items': queryset[:items_per_page],
                'paginator': None,
                'page_obj': None,
                'is_paginated': False,
            }
    
    @staticmethod
    def build_search_query(search_term, search_fields):
        """Build Q object untuk search query"""
        if not search_term or not search_fields:
            return Q()
        
        query = Q()
        for field in search_fields:
            query |= Q(**{f"{field}__icontains": search_term})
        return query
    
    @staticmethod
    def get_date_filter_query(date_field, date_filter):
        """Build date filter query"""
        if not date_filter:
            return Q()
        
        now = timezone.now()
        
        if date_filter == 'today':
            return Q(**{f"{date_field}__date": now.date()})
        elif date_filter == 'yesterday':
            yesterday = now - timedelta(days=1)
            return Q(**{f"{date_field}__date": yesterday.date()})
        elif date_filter == 'this_week':
            start_week = now - timedelta(days=now.weekday())
            return Q(**{f"{date_field}__gte": start_week.replace(hour=0, minute=0, second=0)})
        elif date_filter == 'this_month':
            return Q(**{f"{date_field}__month": now.month, f"{date_filter}__year": now.year})
        elif date_filter == 'this_year':
            return Q(**{f"{date_field}__year": now.year})
        
        return Q()
    
    @staticmethod
    def log_admin_activity(request, action_type, target_object, description=None, changes=None):
        """Log admin activity"""
        try:
            ActivityLog.log_activity(
                actor=request.user if request.user.is_authenticated else None,
                action_type=action_type,
                target_object=target_object,
                description=description,
                changes=changes,
                request=request
            )
        except Exception as e:
            logger.error(f"Error logging activity: {str(e)}")

# ===== AUTHENTICATION CONTROLLER =====

def admin_login(request):
    """Custom admin login view"""
    if request.user.is_authenticated:
        return redirect('admin_panel:dashboard')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        if username and password:
            user = authenticate(request, username=username, password=password)
            if user is not None:
                if user.is_active and user.is_staff:
                    login(request, user)
                    
                    # Log activity
                    BaseAdminController.log_admin_activity(
                        request, 'LOGIN', None,
                        f"User {user.username} logged in"
                    )
                    
                    # Redirect to next page or dashboard
                    next_url = request.GET.get('next')
                    if next_url:
                        return redirect(next_url)
                    else:
                        return redirect('admin_panel:dashboard')
                else:
                    messages.error(request, 'Your account is not active or you do not have admin privileges.')
            else:
                messages.error(request, 'Invalid username or password.')
        else:
            messages.error(request, 'Please provide both username and password.')
    
    return render(request, 'admin_panel/auth/login.html', {
        'form': request.POST if request.method == 'POST' else None
    })

def admin_logout(request):
    """Custom admin logout view"""
    if request.user.is_authenticated:
        # Log activity
        BaseAdminController.log_admin_activity(
            request, 'LOGOUT', None,
            f"User {request.user.username} logged out"
        )
        logout(request)
        messages.success(request, 'You have been logged out successfully.')
    
    return redirect('admin_panel:admin_login')

# ===== DASHBOARD CONTROLLER =====

@login_required(login_url='admin_panel:admin_login')
def admin_dashboard(request):
    """Dashboard utama dengan statistik komprehensif"""
    
    try:
        today = timezone.now().date()
        
        # Basic Statistics
        # Import Theme model
        try:
            from thema.models import Theme
            total_themes = Theme.objects.count()
            active_themes = Theme.objects.filter(is_active=True).count()
        except ImportError:
            total_themes = 0
            active_themes = 0
        
        basic_stats = {
            'total_users': ClientProfile.objects.count(),
            'total_guests': Guest.objects.count(),
            'total_themes': total_themes,
            'active_themes': active_themes,
        }
        
        # User Statistics
        user_stats = {
            'new_users_today': ClientProfile.objects.filter(created_at__date=today).count(),
            'active_subscriptions': ClientProfile.objects.exclude(subscription_type='free').count(),
            'premium_users': ClientProfile.objects.filter(subscription_type__in=['premium', 'gold', 'platinum']).count(),
        }
        
        # Content Statistics
        content_stats = {
            'published_blogs': BlogPost.objects.filter(status='published').count(),
            'draft_blogs': BlogPost.objects.filter(status='draft').count(),
            'total_testimonials': Testimonial.objects.count(),
            'approved_testimonials': Testimonial.objects.filter(is_approved=True).count(),
        }
        
        # Recent Activities
        recent_activities = ActivityLog.objects.select_related('actor').order_by('-timestamp')[:10]
        
        # Recent Users
        recent_users = ClientProfile.objects.select_related('user').order_by('-created_at')[:5]
        
        # Guest Statistics
        guest_stats = {
            'total_guests': Guest.objects.count(),
            'confirmed_guests': RSVPResponse.objects.filter(attendance_status='attending').count(),
            'pending_guests': RSVPResponse.objects.filter(attendance_status='pending').count(),
            'checked_in': CheckInLog.objects.count(),
        }
        
        # Invitation Statistics
        invitation_stats = {
            'total_invitations': Invitation.objects.count(),
            'active_invitations': Invitation.objects.filter(status='active').count(),
            'draft_invitations': Invitation.objects.filter(status='draft').count(),
        }
        
        # Recent Invitations
        recent_invitations = Invitation.objects.select_related('client__user').order_by('-created_at')[:5]
        
        # User registration chart (last 30 days)
        user_registration_data = []
        for i in range(30):
            date = today - timedelta(days=i)
            daily_users = ClientProfile.objects.filter(created_at__date=date).count()
            user_registration_data.append({
                'date': date.strftime('%Y-%m-%d'),
                'users': daily_users
            })
        user_registration_data.reverse()
        
        # System Health Check
        system_health = {
            'database': 'healthy',
            'storage': 'healthy',
            'email': 'healthy',
            'cache': 'healthy',
        }
        
        # Try basic database operation
        try:
            User.objects.count()
        except Exception:
            system_health['database'] = 'error'
        
        # Notifications for admin (REMOVED - AdminNotification model deleted)
        admin_notifications = []  # Placeholder
        
        context = {
            'basic_stats': basic_stats,
            'user_stats': user_stats,
            'content_stats': content_stats,
            'guest_stats': guest_stats,
            'invitation_stats': invitation_stats,
            'recent_activities': recent_activities,
            'recent_users': recent_users,
            'recent_invitations': recent_invitations,
            'user_registration_data': user_registration_data,
            'system_health': system_health,
            'admin_notifications': admin_notifications,
            'current_time': timezone.now(),
            # Financial features removed - set empty defaults
            'financial_stats': {
                'total_revenue': 0,
                'monthly_revenue': 0,
            },
        }
        
        # Log dashboard view
        BaseAdminController.log_admin_activity(
            request, 'view', None, 'Viewed admin dashboard'
        )
        
        return render(request, 'admin_panel/dashboard.html', context)
        
    except Exception as e:
        logger.error(f"Dashboard error: {str(e)}")
        messages.error(request, f"Dashboard error: {str(e)}")
        return render(request, 'admin_panel/dashboard.html', {'error': str(e)})

# ===== THEME MANAGEMENT CONTROLLER ===== (REMOVED - All theme functions deleted)


# ===== USER MANAGEMENT CONTROLLER =====


# ===== USER MANAGEMENT CONTROLLER =====

def user_list(request):
    """Comprehensive user management"""
    
    # Filter parameters
    search = request.GET.get('search', '')
    subscription_filter = request.GET.get('subscription', '')
    status_filter = request.GET.get('status', '')
    date_filter = request.GET.get('date', '')
    sort_by = request.GET.get('sort', '-created_at')
    
    # Base query
    users = ClientProfile.objects.select_related('user').all()
    
    # Apply filters
    if search:
        search_query = BaseAdminController.build_search_query(
            search, ['user__username', 'user__email', 'user__first_name', 'user__last_name', 'phone_number']
        )
        users = users.filter(search_query)
    
    if subscription_filter:
        users = users.filter(subscription_type=subscription_filter)
    
    if status_filter == 'active':
        users = users.filter(user__is_active=True)
    elif status_filter == 'inactive':
        users = users.filter(user__is_active=False)
    
    if date_filter:
        date_query = BaseAdminController.get_date_filter_query('created_at', date_filter)
        users = users.filter(date_query)
    
    # Sorting
    valid_sort_fields = [
        'user__username', '-user__username', 'created_at', '-created_at',
        'subscription_type', 'user__email'
    ]
    if sort_by in valid_sort_fields:
        users = users.order_by(sort_by)
    else:
        users = users.order_by('-created_at')
    
    # Pagination
    pagination_context = BaseAdminController.get_pagination_context(request, users)
    
    # Statistics
    user_stats = {
        'total_users': users.count(),
        'active_users': users.filter(user__is_active=True).count(),
        'premium_users': users.exclude(subscription_type='free').count(),
        'new_this_month': users.filter(
            created_at__gte=timezone.now().replace(day=1)
        ).count(),
    }
    
    context = {
        'current_search': search,
        'current_subscription': subscription_filter,
        'current_status': status_filter,
        'current_date': date_filter,
        'current_sort': sort_by,
        'subscription_choices': ClientProfile.SUBSCRIPTION_CHOICES,
        'user_stats': user_stats,
        **pagination_context
    }
    
    return render(request, 'admin_panel/users/user_list.html', context)


def user_detail(request, pk):
    """Detailed user profile view"""
    
    try:
        client = get_object_or_404(ClientProfile, pk=pk)
        user = client.user
        
        # Get related data
        try:
            groom_info = client.groominfo
        except:
            groom_info = None
            
        try:
            bride_info = client.brideinfo
        except:
            bride_info = None
        
        activities = ActivityLog.objects.filter(actor=user).order_by('-timestamp')[:20]
        
        # Guest statistics
        if groom_info or bride_info:
            guests = Guest.objects.filter(client=client)
            guest_stats = {
                'total_guests': guests.count(),
                'confirmed_guests': guests.filter(rsvpresponse__attendance_status='attending').count(),
                'pending_guests': guests.filter(rsvpresponse__attendance_status='pending').count(),
            }
        else:
            guest_stats = None
        
        context = {
            'client': client,
            'user': user,
            'groom_info': groom_info,
            'bride_info': bride_info,
            'activities': activities,
            'guest_stats': guest_stats,
        }
        
        # Log view
        BaseAdminController.log_admin_activity(
            request, 'view', client, f'Viewed user profile: {user.username}'
        )
        
        return render(request, 'admin_panel/users/user_detail.html', context)
        
    except Exception as e:
        logger.error(f"User detail error: {str(e)}")
        messages.error(request, f"Error loading user details: {str(e)}")
        return redirect('admin_panel:user_list')


@require_POST 
@csrf_exempt
def user_toggle_status(request, pk):
    """Toggle user active status"""
    
    try:
        client = get_object_or_404(ClientProfile, pk=pk)
        user = client.user
        
        user.is_active = not user.is_active
        user.save()
        
        status_text = "activated" if user.is_active else "deactivated"
        
        # Log activity
        BaseAdminController.log_admin_activity(
            request, 'update', client, 
            f'User {user.username} {status_text}',
            changes={'is_active': {'old': not user.is_active, 'new': user.is_active}}
        )
        
        return JsonResponse({
            'status': 'success',
            'is_active': user.is_active,
            'message': f'User "{user.username}" {status_text}!'
        })
        
    except Exception as e:
        logger.error(f"User toggle error: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': f'Error updating user status: {str(e)}'
        }, status=500)


# ===== WHATSAPP MANAGEMENT =====

@login_required
def whatsapp_management(request):
    """Combined WhatsApp management page with numbers and templates"""
    # Get all numbers and templates
    numbers = WhatsAppNumber.objects.all().order_by('-is_default', 'name')
    templates = WhatsAppUserTemplate.objects.all().order_by('template_type', 'template_name')
    has_default = WhatsAppNumber.objects.filter(is_default=True).exists()
    
    context = {
        'numbers': numbers,
        'templates': templates,
        'type_choices': WhatsAppUserTemplate.TEMPLATE_TYPE_CHOICES,
        'has_default': has_default,
    }
    
    return render(request, 'admin_panel/whatsapp/whatsapp.html', context)


@login_required
@require_POST
def whatsapp_number_manage(request, pk=None):
    """Create/Edit WhatsApp number via AJAX"""
    try:
        if pk:
            number = get_object_or_404(WhatsAppNumber, pk=pk)
        else:
            number = None
        
        phone_number = request.POST.get('phone_number', '').strip()
        name = request.POST.get('name', '').strip()
        is_active = request.POST.get('is_active') == 'on'
        is_default = request.POST.get('is_default') == 'on'
        
        if not phone_number:
            return JsonResponse({'status': 'error', 'message': 'Nomor WhatsApp wajib diisi'}, status=400)
        if not name:
            return JsonResponse({'status': 'error', 'message': 'Nama wajib diisi'}, status=400)
        
        # Check if trying to create new number but limit is 1
        if not number:
            existing_count = WhatsAppNumber.objects.count()
            if existing_count >= 1:
                return JsonResponse({'status': 'error', 'message': 'Hanya 1 nomor WhatsApp yang diizinkan'}, status=400)
        
        if number:
            number.phone_number = phone_number
            number.name = name
            number.is_active = is_active
            number.is_default = is_default
            number.save()
            message = 'Nomor WhatsApp berhasil diupdate!'
            BaseAdminController.log_admin_activity(request, 'update', number, f'Updated WhatsApp number: {number.phone_number}')
        else:
            number = WhatsAppNumber.objects.create(
                phone_number=phone_number,
                name=name,
                is_active=is_active,
                is_default=is_default
            )
            message = 'Nomor WhatsApp berhasil ditambahkan!'
            BaseAdminController.log_admin_activity(request, 'create', number, f'Created WhatsApp number: {number.phone_number}')
        
        return JsonResponse({'status': 'success', 'message': message})
    except Exception as e:
        logger.error(f"Error managing WhatsApp number: {str(e)}")
        return JsonResponse({'status': 'error', 'message': f'Error: {str(e)}'}, status=500)


@login_required
@require_POST
def whatsapp_number_delete(request, pk):
    """Delete WhatsApp number"""
    number = get_object_or_404(WhatsAppNumber, pk=pk)
    phone_number = number.phone_number
    number.delete()
    
    BaseAdminController.log_admin_activity(request, 'delete', None, f'Deleted WhatsApp number: {phone_number}')
    
    return JsonResponse({'status': 'success', 'message': f'Nomor WhatsApp {phone_number} berhasil dihapus!'})




@login_required
@require_POST
def whatsapp_template_manage(request, pk=None):
    """Create/Edit WhatsApp user template via AJAX"""
    try:
        if pk:
            template = get_object_or_404(WhatsAppUserTemplate, pk=pk)
        else:
            template = None
        
        template_name = request.POST.get('template_name', '').strip()
        template_type = request.POST.get('template_type', '').strip()
        message_content = request.POST.get('message_content', '').strip()
        is_active = request.POST.get('is_active') == 'on'
        is_default = request.POST.get('is_default') == 'on'
        
        if not template_name:
            return JsonResponse({'status': 'error', 'message': 'Nama template wajib diisi'}, status=400)
        if not template_type:
            return JsonResponse({'status': 'error', 'message': 'Tipe template wajib diisi'}, status=400)
        if not message_content:
            return JsonResponse({'status': 'error', 'message': 'Isi pesan wajib diisi'}, status=400)
        
        if template:
            template.template_name = template_name
            template.template_type = template_type
            template.message_content = message_content
            template.is_active = is_active
            template.is_default = is_default
            template.save()
            message = 'Template berhasil diupdate!'
            BaseAdminController.log_admin_activity(request, 'update', template, f'Updated WhatsApp template: {template.template_name}')
        else:
            template = WhatsAppUserTemplate.objects.create(
                template_name=template_name,
                template_type=template_type,
                message_content=message_content,
                is_active=is_active,
                is_default=is_default
            )
            message = 'Template berhasil ditambahkan!'
            BaseAdminController.log_admin_activity(request, 'create', template, f'Created WhatsApp template: {template.template_name}')
        
        return JsonResponse({'status': 'success', 'message': message})
    except Exception as e:
        logger.error(f"Error managing WhatsApp template: {str(e)}")
        return JsonResponse({'status': 'error', 'message': f'Error: {str(e)}'}, status=500)


@login_required
@require_POST
def whatsapp_template_delete(request, pk):
    """Delete WhatsApp user template"""
    template = get_object_or_404(WhatsAppUserTemplate, pk=pk)
    template_name = template.template_name
    template.delete()
    
    BaseAdminController.log_admin_activity(request, 'delete', None, f'Deleted WhatsApp template: {template_name}')
    
    return JsonResponse({'status': 'success', 'message': f'Template {template_name} berhasil dihapus!'})


# ===== CONTENT MANAGEMENT CONTROLLER =====

def blog_list(request):
    """Blog post management"""
    
    # Filter parameters
    search = request.GET.get('search', '')
    category_filter = request.GET.get('category', '')
    status_filter = request.GET.get('status', '')
    author_filter = request.GET.get('author', '')
    date_filter = request.GET.get('date', '')
    sort_by = request.GET.get('sort', '-created_at')
    
    # Base query
    blog_posts = BlogPost.objects.select_related('category', 'author')
    
    # Apply filters
    if search:
        search_query = BaseAdminController.build_search_query(
            search, ['title', 'excerpt', 'content']
        )
        blog_posts = blog_posts.filter(search_query)
    
    if category_filter:
        blog_posts = blog_posts.filter(category_id=category_filter)
    
    if status_filter:
        blog_posts = blog_posts.filter(status=status_filter)
    
    if author_filter:
        blog_posts = blog_posts.filter(author_id=author_filter)
    
    if date_filter:
        date_query = BaseAdminController.get_date_filter_query('created_at', date_filter)
        blog_posts = blog_posts.filter(date_query)
    
    # Sorting
    valid_sort_fields = [
        'title', '-title', 'created_at', '-created_at', 
        'view_count', '-view_count', 'published_at', '-published_at'
    ]
    if sort_by in valid_sort_fields:
        blog_posts = blog_posts.order_by(sort_by)
    else:
        blog_posts = blog_posts.order_by('-created_at')
    
    # Pagination
    pagination_context = BaseAdminController.get_pagination_context(request, blog_posts)
    
    # Additional data
    categories = BlogCategory.objects.all()
    authors = User.objects.filter(blogpost__isnull=False).distinct()
    
    # Statistics
    blog_stats = {
        'total_posts': blog_posts.count(),
        'published_posts': blog_posts.filter(status='published').count(),
        'draft_posts': blog_posts.filter(status='draft').count(),
        'total_views': blog_posts.aggregate(total_views=Sum('view_count'))['total_views'] or 0,
    }
    
    context = {
        'current_search': search,
        'current_category': category_filter,
        'current_status': status_filter,
        'current_author': author_filter,
        'current_date': date_filter,
        'current_sort': sort_by,
        'categories': categories,
        'authors': authors,
        'status_choices': BlogPost.POST_STATUS_CHOICES,
        'blog_stats': blog_stats,
        **pagination_context
    }
    
    return render(request, 'admin_panel/blog/blog_list.html', context)


# ===== SUPPORT TICKET CONTROLLER =====

# ticket_list function removed - SupportTicket feature not needed for small website


# ===== AJAX UTILITY ENDPOINTS =====

@require_POST
@csrf_exempt
def bulk_action(request):
    """Handle bulk actions across different models"""
    
    try:
        data = json.loads(request.body)
        model_type = data.get('model')
        action = data.get('action')
        item_ids = data.get('item_ids', [])
        
        if not item_ids:
            return JsonResponse({
                'status': 'error',
                'message': 'No items selected!'
            }, status=400)
        
        # Handle different model types
        if model_type == 'user':
            items = ClientProfile.objects.filter(id__in=item_ids)
            model_class = ClientProfile
        elif model_type == 'blog':
            items = BlogPost.objects.filter(id__in=item_ids)
            model_class = BlogPost
        else:
            return JsonResponse({
                'status': 'error',
                'message': 'Invalid model type!'
            }, status=400)
        
        # Perform bulk actions
        count = items.count()
        
        if action == 'activate':
            if model_type == 'user':
                User.objects.filter(clientprofile__in=items).update(is_active=True)
            elif model_type == 'blog':
                items.update(status='published')
            message = f'{count} items activated!'
            
        elif action == 'deactivate':
            if model_type == 'user':
                User.objects.filter(clientprofile__in=items).update(is_active=False)
            elif model_type == 'blog':
                items.update(status='draft')
            message = f'{count} items deactivated!'
            
        elif action == 'delete':
            items.delete()
            message = f'{count} items deleted!'
            
        else:
            return JsonResponse({
                'status': 'error',
                'message': 'Invalid action!'
            }, status=400)
        
        # Log bulk action
        BaseAdminController.log_admin_activity(
            request, 'bulk_action', None,
            f'Bulk {action} on {count} {model_type} items'
        )
        
        return JsonResponse({
            'status': 'success',
            'message': message
        })
        
    except Exception as e:
        logger.error(f"Bulk action error: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': f'Error performing bulk action: {str(e)}'
        }, status=500)


@require_POST
@csrf_exempt
def export_data(request):
    """Export data to CSV"""
    
    try:
        data = json.loads(request.body)
        model_type = data.get('model')
        format_type = data.get('format', 'csv')
        
        if format_type != 'csv':
            return JsonResponse({
                'status': 'error',
                'message': 'Only CSV format is currently supported'
            }, status=400)
        
        # Create HTTP response with CSV content type
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{model_type}_export.csv"'
        
        writer = csv.writer(response)
        
        # Export different model types
        if model_type == 'user':
            writer.writerow(['ID', 'Username', 'Email', 'Subscription', 'Status', 'Joined'])
            users = ClientProfile.objects.select_related('user').all()
            for client in users:
                writer.writerow([
                    client.id, client.user.username, client.user.email,
                    client.get_subscription_type_display(),
                    'Active' if client.user.is_active else 'Inactive',
                    client.created_at.strftime('%Y-%m-%d')
                ])
                
        
        # Log export activity
        BaseAdminController.log_admin_activity(
            request, 'export', None, f'Exported {model_type} data to CSV'
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Export error: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': f'Export failed: {str(e)}'
        }, status=500)


# ===== NOTIFICATION MANAGEMENT =====

@require_POST
@csrf_exempt
def mark_notification_read(request, pk):
    """Mark notification as read"""
    
    try:
        # notification = get_object_or_404(AdminNotification, pk=pk)  # REMOVED - model deleted
        # Placeholder - AdminNotification model removed
        return redirect('admin_panel:dashboard')
        notification.mark_as_read(request.user)
        
        return JsonResponse({
            'status': 'success',
            'message': 'Notification marked as read'
        })
        
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': f'Error: {str(e)}'
        }, status=500)


# ===== USERS MODELS VIEWS =====

@login_required
def client_profile_list(request):
    """List all client profiles"""
    search = request.GET.get('search', '')
    subscription_filter = request.GET.get('subscription', '')
    date_filter = request.GET.get('date_filter', '')
    
    queryset = ClientProfile.objects.select_related('user').all()
    
    # Search
    if search:
        queryset = queryset.filter(
            Q(user__username__icontains=search) |
            Q(user__email__icontains=search) |
            Q(phone_number__icontains=search) |
            Q(city__icontains=search)
        )
    
    # Filter by subscription
    if subscription_filter:
        queryset = queryset.filter(subscription_type=subscription_filter)
    
    # Date filter
    if date_filter:
        date_query = BaseAdminController.get_date_filter_query('created_at', date_filter)
        queryset = queryset.filter(date_query)
    
    queryset = queryset.order_by('-created_at')
    
    # Pagination
    pagination_data = BaseAdminController.get_pagination_context(request, queryset, items_per_page=25)
    
    # Check form completion status for each client
    clients_with_status = []
    for client in pagination_data['items']:
        groom_info = GroomInfo.objects.filter(client=client).first()
        bride_info = BrideInfo.objects.filter(client=client).first()
        main_event = MainEvent.objects.filter(client=client).first()
        reception_event = ReceptionEvent.objects.filter(client=client).first()
        
        form_completed = bool(
            groom_info and bride_info and 
            main_event and reception_event
        )
        
        clients_with_status.append({
            'client': client,
            'form_completed': form_completed
        })
    
    context = {
        'clients_with_status': clients_with_status,
        'page_obj': pagination_data['page_obj'],
        'is_paginated': pagination_data['is_paginated'],
        'has_previous': pagination_data['has_previous'],
        'has_next': pagination_data['has_next'],
        'previous_page_number': pagination_data['previous_page_number'],
        'next_page_number': pagination_data['next_page_number'],
        'search': search,
        'subscription_filter': subscription_filter,
        'date_filter': date_filter,
        'subscription_choices': ClientProfile.SUBSCRIPTION_CHOICES,
        'page_title': 'Client Profiles',
    }
    
    return render(request, 'admin_panel/clients/client_profile_list.html', context)


@login_required
def client_profile_detail(request, pk):
    """Detail view for client profile with all related data"""
    client = get_object_or_404(ClientProfile.objects.select_related('user'), pk=pk)
    
    # Get all related data
    groom_info = GroomInfo.objects.filter(client=client).first()
    bride_info = BrideInfo.objects.filter(client=client).first()
    main_event = MainEvent.objects.filter(client=client).first()
    reception_event = ReceptionEvent.objects.filter(client=client).first()
    
    # QR Manager related
    guests = Guest.objects.filter(client=client)
    guest_groups = GuestGroup.objects.filter(client=client)
    rsvp_responses = RSVPResponse.objects.filter(guest__client=client)
    guest_wishes = GuestWishes.objects.filter(guest__client=client)
    
    # Check if form is completed
    form_completed = bool(
        groom_info and bride_info and 
        main_event and reception_event
    )
    
    # Statistics
    stats = {
        'total_guests': guests.count(),
        'attending_guests': rsvp_responses.filter(attendance_status='attending').count(),
        'total_wishes': guest_wishes.count(),
        'form_completed': form_completed,
    }
    
    BaseAdminController.log_admin_activity(request, 'view', client, f"Viewed client profile: {client.user.username}")
    
    context = {
        'client': client,
        'groom_info': groom_info,
        'bride_info': bride_info,
        'main_event': main_event,
        'reception_event': reception_event,
        'guests': guests,
        'guest_groups': guest_groups,
        'rsvp_responses': rsvp_responses,
        'guest_wishes': guest_wishes,
        'stats': stats,
        'form_completed': form_completed,
        'page_title': f'Client Profile: {client.user.username}',
    }
    
    return render(request, 'admin_panel/clients/client_profile_detail.html', context)


@login_required
def client_profile_download_json(request, pk):
    """Download client profile data as JSON"""
    from django.http import JsonResponse
    from django.utils import timezone
    from datetime import datetime
    
    client = get_object_or_404(ClientProfile.objects.select_related('user'), pk=pk)
    
    # Get all related data
    groom_info = GroomInfo.objects.filter(client=client).first()
    bride_info = BrideInfo.objects.filter(client=client).first()
    main_event = MainEvent.objects.filter(client=client).first()
    reception_event = ReceptionEvent.objects.filter(client=client).first()
    
    # Build JSON data
    def serialize_model(model_instance):
        """Serialize model instance to dict"""
        if not model_instance:
            return None
        
        data = {}
        for field in model_instance._meta.fields:
            value = getattr(model_instance, field.name)
            if isinstance(value, datetime):
                value = value.isoformat()
            elif hasattr(value, 'url'):  # FileField/ImageField
                value = request.build_absolute_uri(value.url) if value else None
            elif hasattr(value, '__str__') and not isinstance(value, (str, int, float, bool, type(None))):
                value = str(value)
            data[field.name] = value
        return data
    
    json_data = {
        'export_info': {
            'exported_at': timezone.now().isoformat(),
            'exported_by': request.user.username,
            'client_id': client.id,
            'client_username': client.user.username,
        },
        'client_profile': serialize_model(client),
        'user_info': {
            'id': client.user.id,
            'username': client.user.username,
            'email': client.user.email,
            'first_name': client.user.first_name,
            'last_name': client.user.last_name,
            'date_joined': client.user.date_joined.isoformat() if client.user.date_joined else None,
        },
        'groom_info': serialize_model(groom_info),
        'bride_info': serialize_model(bride_info),
        'main_event': serialize_model(main_event),
        'reception_event': serialize_model(reception_event),
    }
    
    # Log activity
    BaseAdminController.log_admin_activity(
        request, 'export', client, 
        f"Exported client profile data as JSON: {client.user.username}"
    )
    
    # Return JSON response with download
    response = JsonResponse(json_data, json_dumps_params={'indent': 2, 'ensure_ascii': False})
    response['Content-Disposition'] = f'attachment; filename="client_profile_{client.user.username}_{timezone.now().strftime("%Y%m%d_%H%M%S")}.json"'
    return response


# ===== QR MANAGER VIEWS =====

@login_required
def guest_list(request):
    """List all guests"""
    search = request.GET.get('search', '')
    client_filter = request.GET.get('client', '')
    group_filter = request.GET.get('group', '')
    status_filter = request.GET.get('status', '')
    
    queryset = Guest.objects.select_related('client__user', 'guest_group').all()
    
    # Search
    if search:
        queryset = queryset.filter(
            Q(full_name__icontains=search) |
            Q(phone_number__icontains=search) |
            Q(email__icontains=search) |
            Q(slug__icontains=search)
        )
    
    # Filter by client
    if client_filter:
        queryset = queryset.filter(client_id=client_filter)
    
    # Filter by group
    if group_filter:
        queryset = queryset.filter(guest_group_id=group_filter)
    
    queryset = queryset.order_by('-created_at')
    
    # Pagination
    pagination_data = BaseAdminController.get_pagination_context(request, queryset, items_per_page=25)
    
    # Get filter options
    clients = ClientProfile.objects.all()[:50]
    groups = GuestGroup.objects.all()[:50]
    
    context = {
        'guests': pagination_data['items'],
        'page_obj': pagination_data['page_obj'],
        'is_paginated': pagination_data['is_paginated'],
        'has_previous': pagination_data['has_previous'],
        'has_next': pagination_data['has_next'],
        'previous_page_number': pagination_data['previous_page_number'],
        'next_page_number': pagination_data['next_page_number'],
        'search': search,
        'client_filter': client_filter,
        'group_filter': group_filter,
        'status_filter': status_filter,
        'clients': clients,
        'groups': groups,
        'page_title': 'Guests',
    }
    
    return render(request, 'admin_panel/guests/guest_list.html', context)


@login_required
def guest_detail(request, pk):
    """Detail view for guest with all related data"""
    guest = get_object_or_404(Guest.objects.select_related('client__user', 'guest_group'), pk=pk)
    
    # Get related data
    invitation_code = InvitationCode.objects.filter(guest=guest).first()
    rsvp = RSVPResponse.objects.filter(guest=guest).first()
    wishes = GuestWishes.objects.filter(guest=guest).order_by('-submitted_at')
    check_ins = CheckInLog.objects.filter(guest=guest).order_by('-check_in_time')
    souvenirs = SouvenirLog.objects.filter(guest=guest).order_by('-picked_up_at')
    envelope = DigitalEnvelope.objects.filter(guest=guest).first()
    feedback = GuestFeedback.objects.filter(guest=guest).first()
    whatsapp_logs = WhatsAppLog.objects.filter(guest=guest).order_by('-created_at')
    
    context = {
        'guest': guest,
        'invitation_code': invitation_code,
        'rsvp': rsvp,
        'wishes': wishes,
        'check_ins': check_ins,
        'souvenirs': souvenirs,
        'envelope': envelope,
        'feedback': feedback,
        'whatsapp_logs': whatsapp_logs,
        'page_title': f'Guest: {guest.full_name}',
    }
    
    BaseAdminController.log_admin_activity(request, 'view', guest, f"Viewed guest: {guest.full_name}")
    
    return render(request, 'admin_panel/guests/guest_detail.html', context)


@login_required
def guest_group_list(request):
    """List all guest groups"""
    search = request.GET.get('search', '')
    client_filter = request.GET.get('client', '')
    
    queryset = GuestGroup.objects.select_related('client__user').all()
    
    if search:
        queryset = queryset.filter(
            Q(group_name__icontains=search) |
            Q(description__icontains=search)
        )
    
    if client_filter:
        queryset = queryset.filter(client_id=client_filter)
    
    queryset = queryset.order_by('order', 'group_name')
    
    pagination_data = BaseAdminController.get_pagination_context(request, queryset, items_per_page=25)
    
    context = {
        'groups': pagination_data['items'],
        'page_obj': pagination_data['page_obj'],
        'is_paginated': pagination_data['is_paginated'],
        'search': search,
        'client_filter': client_filter,
        'clients': ClientProfile.objects.all()[:50],
        'page_title': 'Guest Groups',
    }
    
    return render(request, 'admin_panel/guests/guest_group_list.html', context)


@login_required
def rsvp_list(request):
    """List all RSVP responses"""
    search = request.GET.get('search', '')
    status_filter = request.GET.get('status', '')
    
    queryset = RSVPResponse.objects.select_related('guest__client__user', 'guest').all()
    
    if search:
        queryset = queryset.filter(guest__full_name__icontains=search)
    
    if status_filter:
        queryset = queryset.filter(attendance_status=status_filter)
    
    queryset = queryset.order_by('-response_date')
    
    pagination_data = BaseAdminController.get_pagination_context(request, queryset, items_per_page=25)
    
    context = {
        'rsvps': pagination_data['items'],
        'page_obj': pagination_data['page_obj'],
        'is_paginated': pagination_data['is_paginated'],
        'search': search,
        'status_filter': status_filter,
        'status_choices': RSVPResponse.ATTENDANCE_CHOICES,
        'page_title': 'RSVP Responses',
    }
    
    return render(request, 'admin_panel/guests/rsvp_list.html', context)


@login_required
def guest_wishes_list(request):
    """List all guest wishes"""
    search = request.GET.get('search', '')
    approved_filter = request.GET.get('approved', '')
    
    queryset = GuestWishes.objects.select_related('guest__client__user', 'guest').all()
    
    if search:
        queryset = queryset.filter(
            Q(guest__full_name__icontains=search) |
            Q(wish_content__icontains=search)
        )
    
    if approved_filter == 'yes':
        queryset = queryset.filter(is_approved=True)
    elif approved_filter == 'no':
        queryset = queryset.filter(is_approved=False)
    
    queryset = queryset.order_by('-submitted_at')
    
    pagination_data = BaseAdminController.get_pagination_context(request, queryset, items_per_page=25)
    
    context = {
        'wishes': pagination_data['items'],
        'page_obj': pagination_data['page_obj'],
        'is_paginated': pagination_data['is_paginated'],
        'search': search,
        'approved_filter': approved_filter,
        'page_title': 'Guest Wishes',
    }
    
    return render(request, 'admin_panel/guests/guest_wishes_list.html', context)


@login_required
def checkin_list(request):
    """List all check-in logs"""
    search = request.GET.get('search', '')
    event_filter = request.GET.get('event', '')
    
    queryset = CheckInLog.objects.select_related('guest__client__user', 'guest', 'scanned_by').all()
    
    if search:
        queryset = queryset.filter(guest__full_name__icontains=search)
    
    if event_filter:
        queryset = queryset.filter(event_type=event_filter)
    
    queryset = queryset.order_by('-check_in_time')
    
    pagination_data = BaseAdminController.get_pagination_context(request, queryset, items_per_page=25)
    
    context = {
        'checkins': pagination_data['items'],
        'page_obj': pagination_data['page_obj'],
        'is_paginated': pagination_data['is_paginated'],
        'search': search,
        'event_filter': event_filter,
        'event_choices': CheckInLog.EVENT_CHOICES,
        'page_title': 'Check-In Logs',
    }
    
    return render(request, 'admin_panel/guests/checkin_list.html', context)


@login_required
def whatsapp_log_list(request):
    """List all WhatsApp logs"""
    search = request.GET.get('search', '')
    status_filter = request.GET.get('status', '')
    
    queryset = WhatsAppLog.objects.select_related('guest__client__user', 'guest', 'template').all()
    
    if search:
        queryset = queryset.filter(
            Q(guest__full_name__icontains=search) |
            Q(phone_number__icontains=search)
        )
    
    if status_filter:
        queryset = queryset.filter(status=status_filter)
    
    queryset = queryset.order_by('-created_at')
    
    pagination_data = BaseAdminController.get_pagination_context(request, queryset, items_per_page=25)
    
    context = {
        'logs': pagination_data['items'],
        'page_obj': pagination_data['page_obj'],
        'is_paginated': pagination_data['is_paginated'],
        'search': search,
        'status_filter': status_filter,
        'status_choices': WhatsAppLog.STATUS_CHOICES,
        'page_title': 'WhatsApp Logs',
    }
    
    return render(request, 'admin_panel/guests/whatsapp_log_list.html', context)


@login_required
def broadcast_schedule_list(request):
    """List all broadcast schedules"""
    search = request.GET.get('search', '')
    status_filter = request.GET.get('status', '')
    
    queryset = BroadcastSchedule.objects.select_related('client__user', 'template').prefetch_related('target_groups').all()
    
    if search:
        queryset = queryset.filter(broadcast_name__icontains=search)
    
    if status_filter:
        queryset = queryset.filter(status=status_filter)
    
    queryset = queryset.order_by('-scheduled_time')
    
    pagination_data = BaseAdminController.get_pagination_context(request, queryset, items_per_page=25)
    
    context = {
        'broadcasts': pagination_data['items'],
        'page_obj': pagination_data['page_obj'],
        'is_paginated': pagination_data['is_paginated'],
        'search': search,
        'status_filter': status_filter,
        'status_choices': BroadcastSchedule.STATUS_CHOICES,
        'page_title': 'Broadcast Schedules',
    }
    
    return render(request, 'admin_panel/guests/broadcast_schedule_list.html', context)


@login_required
def digital_envelope_list(request):
    """List all digital envelopes"""
    search = request.GET.get('search', '')
    type_filter = request.GET.get('type', '')
    
    queryset = DigitalEnvelope.objects.select_related('guest__client__user', 'guest', 'received_by').all()
    
    if search:
        queryset = queryset.filter(guest__full_name__icontains=search)
    
    if type_filter:
        queryset = queryset.filter(envelope_type=type_filter)
    
    queryset = queryset.order_by('-received_at')
    
    pagination_data = BaseAdminController.get_pagination_context(request, queryset, items_per_page=25)
    
    # Calculate totals
    total_amount = queryset.filter(envelope_type__in=['cash', 'transfer', 'ewallet']).aggregate(
        total=Sum('amount')
    )['total'] or 0
    
    context = {
        'envelopes': pagination_data['items'],
        'page_obj': pagination_data['page_obj'],
        'is_paginated': pagination_data['is_paginated'],
        'search': search,
        'type_filter': type_filter,
        'type_choices': DigitalEnvelope.ENVELOPE_TYPE_CHOICES,
        'total_amount': total_amount,
        'page_title': 'Digital Envelopes',
    }
    
    return render(request, 'admin_panel/guests/digital_envelope_list.html', context)


@login_required
def guest_feedback_list(request):
    """List all guest feedback"""
    search = request.GET.get('search', '')
    rating_filter = request.GET.get('rating', '')
    
    queryset = GuestFeedback.objects.select_related('guest__client__user', 'guest').all()
    
    if search:
        queryset = queryset.filter(
            Q(guest__full_name__icontains=search) |
            Q(feedback_text__icontains=search)
        )
    
    if rating_filter:
        queryset = queryset.filter(rating=rating_filter)
    
    queryset = queryset.order_by('-submitted_at')
    
    pagination_data = BaseAdminController.get_pagination_context(request, queryset, items_per_page=25)
    
    # Calculate average rating
    avg_rating = queryset.aggregate(avg=Avg('rating'))['avg'] or 0
    
    context = {
        'feedbacks': pagination_data['items'],
        'page_obj': pagination_data['page_obj'],
        'is_paginated': pagination_data['is_paginated'],
        'search': search,
        'rating_filter': rating_filter,
        'rating_choices': GuestFeedback.RATING_CHOICES,
        'avg_rating': round(avg_rating, 2),
        'page_title': 'Guest Feedback',
    }
    
    return render(request, 'admin_panel/guests/guest_feedback_list.html', context)


# ===== CORE MODELS VIEWS =====

@login_required
def pricing_package_list(request):
    """List all pricing packages"""
    search = request.GET.get('search', '')
    type_filter = request.GET.get('type', '')
    active_filter = request.GET.get('active', '')
    
    queryset = PricingPackage.objects.prefetch_related('features').all()
    
    if search:
        queryset = queryset.filter(
            Q(package_name__icontains=search) |
            Q(description__icontains=search)
        )
    
    if type_filter:
        queryset = queryset.filter(package_type=type_filter)
    
    if active_filter == 'yes':
        queryset = queryset.filter(is_active=True)
    elif active_filter == 'no':
        queryset = queryset.filter(is_active=False)
    
    queryset = queryset.order_by('order', 'price')
    
    pagination_data = BaseAdminController.get_pagination_context(request, queryset, items_per_page=25)
    
    context = {
        'packages': pagination_data['items'],
        'page_obj': pagination_data['page_obj'],
        'is_paginated': pagination_data['is_paginated'],
        'search': search,
        'type_filter': type_filter,
        'active_filter': active_filter,
        'type_choices': PricingPackage.PACKAGE_TYPE_CHOICES,
        'page_title': 'Pricing Packages',
    }
    
    return render(request, 'admin_panel/pricing/pricing_package_list.html', context)


@login_required
def pricing_package_detail(request, pk):
    """Detail view for pricing package"""
    package = get_object_or_404(PricingPackage.objects.prefetch_related('features'), pk=pk)
    features = package.features.all().order_by('order')
    
    context = {
        'package': package,
        'features': features,
        'page_title': f'Package: {package.package_name}',
    }
    
    BaseAdminController.log_admin_activity(request, 'view', package, f"Viewed pricing package: {package.package_name}")
    
    return render(request, 'admin_panel/pricing/pricing_package_detail.html', context)


@login_required
def discount_coupon_list(request):
    """List all discount coupons"""
    search = request.GET.get('search', '')
    status_filter = request.GET.get('status', '')
    
    queryset = DiscountCoupon.objects.prefetch_related('applicable_packages').all()
    
    if search:
        queryset = queryset.filter(
            Q(coupon_code__icontains=search) |
            Q(coupon_name__icontains=search)
        )
    
    if status_filter:
        queryset = queryset.filter(status=status_filter)
    
    queryset = queryset.order_by('-created_at')
    
    pagination_data = BaseAdminController.get_pagination_context(request, queryset, items_per_page=25)
    
    context = {
        'coupons': pagination_data['items'],
        'page_obj': pagination_data['page_obj'],
        'is_paginated': pagination_data['is_paginated'],
        'search': search,
        'status_filter': status_filter,
        'status_choices': DiscountCoupon.COUPON_STATUS_CHOICES,
        'page_title': 'Discount Coupons',
    }
    
    return render(request, 'admin_panel/pricing/discount_coupon_list.html', context)


@login_required
def payment_method_list(request):
    """List all payment methods"""
    search = request.GET.get('search', '')
    type_filter = request.GET.get('type', '')
    
    queryset = PaymentMethod.objects.all()
    
    if search:
        queryset = queryset.filter(
            Q(method_name__icontains=search) |
            Q(bank_name__icontains=search)
        )
    
    if type_filter:
        queryset = queryset.filter(method_type=type_filter)
    
    queryset = queryset.order_by('order', 'method_name')
    
    pagination_data = BaseAdminController.get_pagination_context(request, queryset, items_per_page=25)
    
    context = {
        'methods': pagination_data['items'],
        'page_obj': pagination_data['page_obj'],
        'is_paginated': pagination_data['is_paginated'],
        'search': search,
        'type_filter': type_filter,
        'type_choices': PaymentMethod.METHOD_TYPE_CHOICES,
        'page_title': 'Payment Methods',
    }
    
    return render(request, 'admin_panel/pricing/payment_method_list.html', context)


@login_required
def refund_request_list(request):
    """List all refund requests"""
    search = request.GET.get('search', '')
    status_filter = request.GET.get('status', '')
    
    queryset = RefundRequest.objects.select_related('transaction__user', 'requested_by', 'approved_by').all()
    
    if search:
        queryset = queryset.filter(
            Q(transaction__transaction_id__icontains=search) |
            Q(requested_by__username__icontains=search)
        )
    
    if status_filter:
        queryset = queryset.filter(status=status_filter)
    
    queryset = queryset.order_by('-requested_at')
    
    pagination_data = BaseAdminController.get_pagination_context(request, queryset, items_per_page=25)
    
    context = {
        'refunds': pagination_data['items'],
        'page_obj': pagination_data['page_obj'],
        'is_paginated': pagination_data['is_paginated'],
        'search': search,
        'status_filter': status_filter,
        'status_choices': RefundRequest.REFUND_STATUS_CHOICES,
        'page_title': 'Refund Requests',
    }
    
    return render(request, 'admin_panel/pricing/refund_request_list.html', context)


@login_required
def faq_list(request):
    """List all FAQ items"""
    search = request.GET.get('search', '')
    category_filter = request.GET.get('category', '')
    
    queryset = FaqItem.objects.select_related('created_by').all()
    
    if search:
        queryset = queryset.filter(
            Q(question__icontains=search) |
            Q(answer__icontains=search)
        )
    
    if category_filter:
        queryset = queryset.filter(category=category_filter)
    
    queryset = queryset.order_by('category', 'order')
    
    pagination_data = BaseAdminController.get_pagination_context(request, queryset, items_per_page=25)
    
    context = {
        'faqs': pagination_data['items'],
        'page_obj': pagination_data['page_obj'],
        'is_paginated': pagination_data['is_paginated'],
        'search': search,
        'category_filter': category_filter,
        'category_choices': FaqItem.FAQ_CATEGORY_CHOICES,
        'page_title': 'FAQ Items',
    }
    
    return render(request, 'admin_panel/content/faq_list.html', context)


@login_required
def testimonial_list(request):
    """List all testimonials"""
    search = request.GET.get('search', '')
    approved_filter = request.GET.get('approved', '')
    rating_filter = request.GET.get('rating', '')
    
    queryset = Testimonial.objects.select_related('user').all()
    
    if search:
        queryset = queryset.filter(
            Q(client_name__icontains=search) |
            Q(testimonial_text__icontains=search)
        )
    
    if approved_filter == 'yes':
        queryset = queryset.filter(is_approved=True)
    elif approved_filter == 'no':
        queryset = queryset.filter(is_approved=False)
    
    if rating_filter:
        queryset = queryset.filter(rating=rating_filter)
    
    queryset = queryset.order_by('display_order', '-created_at')
    
    pagination_data = BaseAdminController.get_pagination_context(request, queryset, items_per_page=25)
    
    # Calculate average rating
    avg_rating = queryset.aggregate(avg=Avg('rating'))['avg'] or 0
    
    context = {
        'testimonials': pagination_data['items'],
        'page_obj': pagination_data['page_obj'],
        'is_paginated': pagination_data['is_paginated'],
        'search': search,
        'approved_filter': approved_filter,
        'rating_filter': rating_filter,
        'rating_choices': Testimonial.RATING_CHOICES,
        'avg_rating': round(avg_rating, 2),
        'page_title': 'Testimonials',
    }
    
    return render(request, 'admin_panel/content/testimonial_list.html', context)


@login_required
def partner_vendor_list(request):
    """List all partner vendors"""
    search = request.GET.get('search', '')
    type_filter = request.GET.get('type', '')
    
    queryset = PartnerVendor.objects.all()
    
    if search:
        queryset = queryset.filter(
            Q(vendor_name__icontains=search) |
            Q(contact_person__icontains=search) |
            Q(city__icontains=search)
        )
    
    if type_filter:
        queryset = queryset.filter(vendor_type=type_filter)
    
    queryset = queryset.order_by('vendor_type', 'order', 'vendor_name')
    
    pagination_data = BaseAdminController.get_pagination_context(request, queryset, items_per_page=25)
    
    context = {
        'vendors': pagination_data['items'],
        'page_obj': pagination_data['page_obj'],
        'is_paginated': pagination_data['is_paginated'],
        'search': search,
        'type_filter': type_filter,
        'type_choices': PartnerVendor.VENDOR_TYPE_CHOICES,
        'page_title': 'Partner Vendors',
    }
    
    return render(request, 'admin_panel/content/partner_vendor_list.html', context)


@login_required
def site_configuration(request):
    """Website settings/configuration"""
    config = SiteConfiguration.objects.first()
    
    if not config:
        config = SiteConfiguration.objects.create(
            site_name="Invywed",
            contact_email="admin@invywed.com",
            contact_phone="+62",
            contact_whatsapp="+62",
            contact_address=""
        )
    
    if request.method == 'POST':
        # Update configuration
        config.site_name = request.POST.get('site_name', config.site_name)
        config.site_tagline = request.POST.get('site_tagline', config.site_tagline)
        config.site_description = request.POST.get('site_description', config.site_description)
        config.contact_email = request.POST.get('contact_email', config.contact_email)
        config.contact_phone = request.POST.get('contact_phone', config.contact_phone)
        config.contact_whatsapp = request.POST.get('contact_whatsapp', config.contact_whatsapp)
        config.contact_address = request.POST.get('contact_address', config.contact_address)
        config.social_facebook = request.POST.get('social_facebook', config.social_facebook)
        config.social_instagram = request.POST.get('social_instagram', config.social_instagram)
        config.social_twitter = request.POST.get('social_twitter', config.social_twitter)
        config.social_youtube = request.POST.get('social_youtube', config.social_youtube)
        config.social_tiktok = request.POST.get('social_tiktok', config.social_tiktok)
        config.google_analytics_id = request.POST.get('google_analytics_id', config.google_analytics_id)
        config.maintenance_mode = request.POST.get('maintenance_mode') == 'on'
        config.maintenance_message = request.POST.get('maintenance_message', config.maintenance_message)
        config.seo_title = request.POST.get('seo_title', config.seo_title)
        config.seo_description = request.POST.get('seo_description', config.seo_description)
        config.seo_keywords = request.POST.get('seo_keywords', config.seo_keywords)
        
        if 'site_logo' in request.FILES:
            config.site_logo = request.FILES['site_logo']
        if 'site_favicon' in request.FILES:
            config.site_favicon = request.FILES['site_favicon']
        
        config.save()
        
        BaseAdminController.log_admin_activity(request, 'update', config, "Updated site configuration")
        messages.success(request, 'Site configuration updated successfully!')
        return redirect('admin_panel:site_configuration')
    
    context = {
        'config': config,
        'page_title': 'Site Configuration',
    }
    
    return render(request, 'admin_panel/settings/site_configuration.html', context)


@login_required
def maintenance_log_list(request):
    """List all maintenance logs"""
    search = request.GET.get('search', '')
    type_filter = request.GET.get('type', '')
    
    queryset = MaintenanceLog.objects.select_related('performed_by').all()
    
    if search:
        queryset = queryset.filter(title__icontains=search)
    
    if type_filter:
        queryset = queryset.filter(log_type=type_filter)
    
    queryset = queryset.order_by('-started_at')
    
    pagination_data = BaseAdminController.get_pagination_context(request, queryset, items_per_page=25)
    
    context = {
        'logs': pagination_data['items'],
        'page_obj': pagination_data['page_obj'],
        'is_paginated': pagination_data['is_paginated'],
        'search': search,
        'type_filter': type_filter,
        'type_choices': MaintenanceLog.LOG_TYPE_CHOICES,
        'page_title': 'Maintenance Logs',
    }
    
    return render(request, 'admin_panel/settings/maintenance_log_list.html', context)


# ===== EDITOR VIEWS =====

@login_required
@user_passes_test(lambda u: u.is_staff or u.is_superuser)
def editor_template_list(request):
    """List semua template undangan dengan opsi upload - REMOVED (Theme model deleted)"""
    messages.info(request, 'Template editor telah dinonaktifkan karena model Theme telah dihapus.')
    return redirect('admin_panel:dashboard')


def inject_css_js_to_html(html_content, css_url, js_url):
    """
    Inject CSS and JS links into HTML <head> section automatically.
    If CSS/JS files exist, add <link> and <script> tags before </head>
    """
    import re
    
    # Check if CSS/JS already exists in HTML to avoid duplicates
    has_css_link = bool(re.search(r'<link[^>]*href=["\']?[^"\']*style\.css', html_content, re.I))
    has_js_script = bool(re.search(r'<script[^>]*src=["\']?[^"\']*script\.js', html_content, re.I))
    
    # Build injection string
    injection_parts = []
    
    if css_url and not has_css_link:
        injection_parts.append(f'<link rel="stylesheet" href="{css_url}">')
    
    if js_url and not has_js_script:
        injection_parts.append(f'<script src="{js_url}"></script>')
    
    if not injection_parts:
        return html_content
    
    injection = '\n    '.join(injection_parts)
    
    # Try to inject before </head>
    if re.search(r'</head>', html_content, re.I):
        html_content = re.sub(
            r'(</head>)',
            f'    {injection}\n\\1',
            html_content,
            flags=re.IGNORECASE
        )
    # If no </head> found, try before </body>
    elif re.search(r'</body>', html_content, re.I):
        # For JS, inject before </body> is better
        js_only = f'<script src="{js_url}"></script>' if js_url and not has_js_script else ''
        css_only = f'<link rel="stylesheet" href="{css_url}">' if css_url and not has_css_link else ''
        
        if css_only:
            # CSS should be in head, so try to find <head> tag
            if re.search(r'<head[^>]*>', html_content, re.I):
                html_content = re.sub(
                    r'(<head[^>]*>)',
                    f'\\1\n    {css_only}',
                    html_content,
                    flags=re.IGNORECASE
                )
            else:
                # No head tag, add CSS at beginning
                html_content = css_only + '\n' + html_content
        
        if js_only:
            html_content = re.sub(
                r'(</body>)',
                f'    {js_only}\n\\1',
                html_content,
                flags=re.IGNORECASE
            )
    # If no </head> or </body>, prepend to HTML
    else:
        html_content = '\n'.join(injection_parts) + '\n' + html_content
    
    return html_content


@login_required
@user_passes_test(lambda u: u.is_staff or u.is_superuser)
def editor_template_upload(request):
    """Upload template HTML baru dengan struktur folder per template"""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Method not allowed'}, status=405)
    
    try:
        name = request.POST.get('name', '').strip()
        html_file = request.FILES.get('html_file')
        category_id = request.POST.get('category')
        
        if not name:
            return JsonResponse({'status': 'error', 'message': 'Nama template wajib diisi'}, status=400)
        
        if not html_file:
            return JsonResponse({'status': 'error', 'message': 'File HTML wajib diupload'}, status=400)
        
        if not category_id:
            return JsonResponse({'status': 'error', 'message': 'Kategori wajib dipilih'}, status=400)
        
        category = get_object_or_404(Category, id=category_id, is_active=True)
        
        return JsonResponse({'status': 'error', 'message': 'Template editor telah dinonaktifkan karena model Theme telah dihapus.'}, status=400)
        
    except Exception as e:
        logger.error(f"Error uploading template: {str(e)}")
        return JsonResponse({'status': 'error', 'message': f'Error: {str(e)}'}, status=500)


@login_required
@user_passes_test(lambda u: u.is_staff or u.is_superuser)
def editor_template_edit(request, pk):
    """Editor template untuk melihat endpoint dan informasi - dengan support CSS, JS, dan images
    REMOVED: Theme model telah dihapus, fungsi ini dinonaktifkan
    """
    # Theme model removed - editor disabled
    messages.error(request, 'Template editor telah dinonaktifkan karena model Theme telah dihapus.')
    return redirect('admin_panel:dashboard')


# ===== INVITATION MANAGEMENT VIEWS =====

@login_required(login_url='admin_panel:admin_login')
def invitation_list(request):
    """List semua undangan"""
    # Check permission
    if not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, 'Anda tidak memiliki izin untuk mengakses halaman ini.')
        return redirect('admin_panel:dashboard')
    
    # Get all invitations
    invitations = Invitation.objects.select_related('client__user').order_by('-created_at')
    
    # Search
    search_query = request.GET.get('search', '')
    if search_query:
        invitations = invitations.filter(
            Q(invitation_slug__icontains=search_query) |
            Q(client__user__username__icontains=search_query) |
            Q(client__user__first_name__icontains=search_query) |
            Q(client__user__last_name__icontains=search_query)
        )
    
    # Filter by status
    status_filter = request.GET.get('status', '')
    if status_filter:
        invitations = invitations.filter(status=status_filter)
    
    # Statistics
    all_invitations = Invitation.objects.all()
    stats = {
        'total': all_invitations.count(),
        'active': all_invitations.filter(status='active').count(),
        'draft': all_invitations.filter(status='draft').count(),
        'inactive': all_invitations.filter(status='inactive').count(),
    }
    
    # Pagination
    paginator = Paginator(invitations, 20)
    page = request.GET.get('page', 1)
    try:
        invitations_page = paginator.page(page)
    except PageNotAnInteger:
        invitations_page = paginator.page(1)
    except EmptyPage:
        invitations_page = paginator.page(paginator.num_pages)
    
    # All invitations in the list
    
    # Check permissions for each invitation (can delete or not)
    # For admin: can delete any invitation
    # For users: can only delete invitations they created (not created by admin)
    is_admin = request.user.is_staff or request.user.is_superuser
    invitation_permissions = {}
    
    if not is_admin:
        # For regular users, check creation logs
        from .models import ActivityLog
        from django.contrib.contenttypes.models import ContentType
        
        invitation_ct = ContentType.objects.get_for_model(Invitation)
        for invitation in invitations_page:
            creation_log = ActivityLog.objects.filter(
                target_content_type=invitation_ct,
                target_object_id=invitation.pk,
                action_type='create'
            ).order_by('-timestamp').first()
            
            can_delete = False
            if creation_log and creation_log.actor:
                # Can delete if user created it AND it was not created by admin
                if creation_log.actor == request.user and not (creation_log.actor.is_staff or creation_log.actor.is_superuser):
                    can_delete = True
            else:
                # If no creation log, assume user can delete (for backward compatibility)
                can_delete = True
            
            invitation_permissions[invitation.pk] = {
                'can_delete': can_delete,
                'can_edit': False,  # Users cannot edit invitations (per requirement)
            }
    else:
        # Admin can delete and edit all invitations
        for invitation in invitations_page:
            invitation_permissions[invitation.pk] = {
                'can_delete': True,
                'can_edit': True,
            }
    
    context = {
        'invitations': invitations_page,
        'search_query': search_query,
        'status_filter': status_filter,
        'stats': stats,
        'invitation_permissions': invitation_permissions,
        'is_admin': is_admin,
    }
    
    return render(request, 'admin_panel/invitations/invitation_list.html', context)


@login_required(login_url='admin_panel:admin_login')
def invitation_manage(request, pk=None):
    """Create atau edit invitation dengan semua data lengkap"""
    # Check permission
    if not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, 'Anda tidak memiliki izin untuk mengakses halaman ini.')
        return redirect('admin_panel:dashboard')
    
    invitation = None
    mode = 'create'
    
    if pk:
        invitation = get_object_or_404(Invitation, pk=pk)
        mode = 'edit'
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # For edit mode, use existing client
                if mode == 'edit':
                    client = invitation.client
                else:
                    # CREATE MODE: Either use existing user or create new user
                    user_option = request.POST.get('user_option', 'existing')
                    
                    if user_option == 'existing':
                        # Use existing user
                        existing_user_id = request.POST.get('existing_user')
                        if not existing_user_id:
                            messages.error(request, 'Pilih user yang sudah ada')
                            return redirect('admin_panel:invitation_add')
                        
                        client = get_object_or_404(ClientProfile, pk=existing_user_id)
                    else:
                        # CREATE MODE: Create new User and ClientProfile
                        # User data
                        username = request.POST.get('username', '').strip()
                        email = request.POST.get('email', '').strip()
                        first_name = request.POST.get('first_name', '').strip()
                        last_name = request.POST.get('last_name', '').strip()
                        password = request.POST.get('password', '').strip()
                        
                        if not username or not email:
                            messages.error(request, 'Username dan Email wajib diisi')
                            return redirect('admin_panel:invitation_add')
                        
                        # Check if user exists
                        if User.objects.filter(username=username).exists() or User.objects.filter(email=email).exists():
                            messages.error(request, 'Username atau Email sudah digunakan')
                            return redirect('admin_panel:invitation_add')
                        
                        # Generate password if not provided (format: invywed + 5 random digits)
                        if not password:
                            import random
                            random_numbers = random.randint(10000, 99999)
                            password = f'invywed{random_numbers}'
                        
                        # Create user
                        user = User.objects.create_user(
                            username=username,
                            email=email,
                            password=password,
                            first_name=first_name,
                            last_name=last_name
                        )
                        
                        # ClientProfile data
                        phone_number = request.POST.get('phone_number', '').strip()
                        whatsapp_number = request.POST.get('whatsapp_number', '').strip()
                        address = request.POST.get('address', '').strip()
                        city = request.POST.get('city', '').strip()
                        profile_photo = request.FILES.get('profile_photo')
                        
                        # Validate phone_number (required for new user)
                        if not phone_number:
                            messages.error(request, 'Nomor telepon wajib diisi untuk user baru')
                            raise ValidationError('Nomor telepon wajib diisi')
                        
                        # Create ClientProfile
                        # Use empty string for optional fields if not provided
                        client = ClientProfile.objects.create(
                            user=user,
                            phone_number=phone_number,
                            whatsapp_number=whatsapp_number or phone_number or '',
                            address=address or '',
                            city=city or '',
                            profile_photo=profile_photo
                        )
                
                # Groom Info
                groom_full_name = request.POST.get('groom_full_name', '').strip()
                groom_nickname = request.POST.get('groom_nickname', '').strip()
                groom_father_name = request.POST.get('groom_father_name', '').strip()
                groom_mother_name = request.POST.get('groom_mother_name', '').strip()
                groom_child_order = request.POST.get('groom_child_order', '').strip()
                groom_main_photo = request.FILES.get('groom_main_photo')
                
                # Groom Info - optional, save if any field is provided
                if groom_full_name or groom_nickname or groom_father_name or groom_mother_name or groom_main_photo:
                    # Use update_or_create to safely handle OneToOneField
                    defaults = {}
                    if groom_full_name:
                        defaults['full_name'] = groom_full_name
                    if groom_nickname:
                        defaults['nickname'] = groom_nickname
                    if groom_father_name:
                        defaults['father_name'] = groom_father_name
                    if groom_mother_name:
                        defaults['mother_name'] = groom_mother_name
                    if groom_child_order:
                        defaults['child_order'] = groom_child_order
                    if groom_main_photo:
                        defaults['main_photo'] = groom_main_photo
                    
                    # Only create if full_name is provided (required field)
                    if groom_full_name:
                        groom, created = GroomInfo.objects.update_or_create(
                            client=client,
                            defaults={
                                'full_name': groom_full_name,
                                'nickname': groom_nickname or '',
                                'father_name': groom_father_name or '',
                                'mother_name': groom_mother_name or '',
                                'child_order': groom_child_order or '',
                                'main_photo': groom_main_photo if groom_main_photo else None
                            }
                        )
                    elif groom_main_photo:
                        # If no full_name but has photo, check if exists first
                        groom = GroomInfo.objects.filter(client=client).first()
                        if groom:
                            groom.main_photo = groom_main_photo
                            groom.save()
                        else:
                            groom = GroomInfo.objects.create(
                                client=client,
                                full_name='Mempelai Pria',
                                main_photo=groom_main_photo
                            )
                    else:
                        # Update existing only
                        groom = GroomInfo.objects.filter(client=client).first()
                        if groom:
                            if groom_nickname:
                                groom.nickname = groom_nickname
                            if groom_father_name:
                                groom.father_name = groom_father_name
                            if groom_mother_name:
                                groom.mother_name = groom_mother_name
                            if groom_child_order:
                                groom.child_order = groom_child_order
                            groom.save()
                
                # Bride Info
                bride_full_name = request.POST.get('bride_full_name', '').strip()
                bride_nickname = request.POST.get('bride_nickname', '').strip()
                bride_father_name = request.POST.get('bride_father_name', '').strip()
                bride_mother_name = request.POST.get('bride_mother_name', '').strip()
                bride_child_order = request.POST.get('bride_child_order', '').strip()
                bride_main_photo = request.FILES.get('bride_main_photo')
                
                # Bride Info - optional, save if any field is provided
                if bride_full_name or bride_nickname or bride_father_name or bride_mother_name or bride_main_photo:
                    # Use update_or_create to safely handle OneToOneField
                    if bride_full_name:
                        bride, created = BrideInfo.objects.update_or_create(
                            client=client,
                            defaults={
                                'full_name': bride_full_name,
                                'nickname': bride_nickname or '',
                                'father_name': bride_father_name or '',
                                'mother_name': bride_mother_name or '',
                                'child_order': bride_child_order or '',
                                'main_photo': bride_main_photo if bride_main_photo else None
                            }
                        )
                    elif bride_main_photo:
                        # If no full_name but has photo, check if exists first
                        bride = BrideInfo.objects.filter(client=client).first()
                        if bride:
                            bride.main_photo = bride_main_photo
                            bride.save()
                        else:
                            bride = BrideInfo.objects.create(
                                client=client,
                                full_name='Mempelai Wanita',
                                main_photo=bride_main_photo
                            )
                    else:
                        # Update existing only
                        bride = BrideInfo.objects.filter(client=client).first()
                        if bride:
                            if bride_nickname:
                                bride.nickname = bride_nickname
                            if bride_father_name:
                                bride.father_name = bride_father_name
                            if bride_mother_name:
                                bride.mother_name = bride_mother_name
                            if bride_child_order:
                                bride.child_order = bride_child_order
                            bride.save()
                
                # Main Event (Akad)
                main_event_name = request.POST.get('main_event_name', 'Akad Nikah').strip()
                main_event_date = request.POST.get('main_event_date')
                main_start_time = request.POST.get('main_start_time')
                main_end_time = request.POST.get('main_end_time')
                main_timezone = request.POST.get('main_timezone', 'WIB')
                main_venue_name = request.POST.get('main_venue_name', '').strip()
                main_venue_address = request.POST.get('main_venue_address', '').strip()
                main_venue_phone = request.POST.get('main_venue_phone', '').strip()
                main_google_maps_url = request.POST.get('main_google_maps_url', '').strip()
                main_venue_photo = request.FILES.get('main_venue_photo')
                main_special_notes = request.POST.get('main_special_notes', '').strip()
                
                # Main Event - optional, save only if required fields are provided
                if main_event_date and main_start_time and main_venue_name and main_venue_address:
                    from django.utils.dateparse import parse_date, parse_time
                    
                    parsed_date = parse_date(main_event_date)
                    parsed_time = parse_time(main_start_time) if main_start_time else None
                    parsed_end_time = parse_time(main_end_time) if main_end_time else None
                    
                    # Use update_or_create to safely handle OneToOneField
                    main_event, created = MainEvent.objects.update_or_create(
                        client=client,
                        defaults={
                            'event_name': main_event_name or 'Akad Nikah',
                            'event_date': parsed_date,
                            'start_time': parsed_time,
                            'end_time': parsed_end_time,
                            'timezone': main_timezone or 'WIB',
                            'venue_name': main_venue_name,
                            'venue_address': main_venue_address,
                            'venue_phone': main_venue_phone or '',
                            'google_maps_url': main_google_maps_url or '',
                            'special_notes': main_special_notes or '',
                            'venue_photo': main_venue_photo if main_venue_photo else None
                        }
                    )
                elif main_event_date or main_start_time or main_venue_name or main_venue_address or main_venue_photo:
                    # If some fields provided but not all required ones, update existing if exists
                    try:
                        main_event = MainEvent.objects.get(client=client)
                        from django.utils.dateparse import parse_date, parse_time
                        
                        if main_event_name:
                            main_event.event_name = main_event_name
                        if main_event_date:
                            parsed_date = parse_date(main_event_date)
                            if parsed_date:
                                main_event.event_date = parsed_date
                        if main_start_time:
                            parsed_time = parse_time(main_start_time)
                            if parsed_time:
                                main_event.start_time = parsed_time
                        if main_end_time:
                            parsed_end_time = parse_time(main_end_time)
                            if parsed_end_time:
                                main_event.end_time = parsed_end_time
                        if main_timezone:
                            main_event.timezone = main_timezone
                        if main_venue_name:
                            main_event.venue_name = main_venue_name
                        if main_venue_address:
                            main_event.venue_address = main_venue_address
                        if main_venue_phone:
                            main_event.venue_phone = main_venue_phone
                        if main_google_maps_url:
                            main_event.google_maps_url = main_google_maps_url
                        if main_special_notes:
                            main_event.special_notes = main_special_notes
                        if main_venue_photo:
                            main_event.venue_photo = main_venue_photo
                        
                        main_event.save()
                    except MainEvent.DoesNotExist:
                        pass  # Skip if doesn't exist and required fields not complete
                
                # Reception Event (optional)
                reception_event_name = request.POST.get('reception_event_name', 'Resepsi Pernikahan').strip()
                reception_event_date = request.POST.get('reception_event_date')
                reception_start_time = request.POST.get('reception_start_time')
                reception_end_time = request.POST.get('reception_end_time')
                reception_timezone = request.POST.get('reception_timezone', 'WIB')
                reception_venue_name = request.POST.get('reception_venue_name', '').strip()
                reception_venue_address = request.POST.get('reception_venue_address', '').strip()
                reception_venue_phone = request.POST.get('reception_venue_phone', '').strip()
                reception_google_maps_url = request.POST.get('reception_google_maps_url', '').strip()
                reception_venue_photo = request.FILES.get('reception_venue_photo')
                reception_dress_code = request.POST.get('reception_dress_code', '').strip()
                reception_adab_walimah = request.POST.get('reception_adab_walimah', '').strip()
                reception_special_notes = request.POST.get('reception_special_notes', '').strip()
                
                # Reception Event - optional, save only if required fields are provided
                if reception_event_date and reception_start_time and reception_venue_name and reception_venue_address:
                    from django.utils.dateparse import parse_date, parse_time
                    
                    parsed_date = parse_date(reception_event_date)
                    parsed_time = parse_time(reception_start_time) if reception_start_time else None
                    parsed_end_time = parse_time(reception_end_time) if reception_end_time else None
                    
                    # Use update_or_create to safely handle OneToOneField
                    reception_event, created = ReceptionEvent.objects.update_or_create(
                        client=client,
                        defaults={
                            'event_name': reception_event_name or 'Resepsi Pernikahan',
                            'event_date': parsed_date,
                            'start_time': parsed_time,
                            'end_time': parsed_end_time,
                            'timezone': reception_timezone or 'WIB',
                            'venue_name': reception_venue_name,
                            'venue_address': reception_venue_address,
                            'venue_phone': reception_venue_phone or '',
                            'google_maps_url': reception_google_maps_url or '',
                            'dress_code': reception_dress_code or '',
                            'adab_walimah': reception_adab_walimah or '',
                            'special_notes': reception_special_notes or '',
                            'venue_photo': reception_venue_photo if reception_venue_photo else None
                        }
                    )
                elif reception_event_date or reception_start_time or reception_venue_name or reception_venue_address or reception_venue_photo:
                    # If some fields provided but not all required ones, update existing if exists
                    try:
                        reception_event = ReceptionEvent.objects.get(client=client)
                        from django.utils.dateparse import parse_date, parse_time
                        
                        if reception_event_name:
                            reception_event.event_name = reception_event_name
                        if reception_event_date:
                            parsed_date = parse_date(reception_event_date)
                            if parsed_date:
                                reception_event.event_date = parsed_date
                        if reception_start_time:
                            parsed_time = parse_time(reception_start_time)
                            if parsed_time:
                                reception_event.start_time = parsed_time
                        if reception_end_time:
                            parsed_end_time = parse_time(reception_end_time)
                            if parsed_end_time:
                                reception_event.end_time = parsed_end_time
                        if reception_timezone:
                            reception_event.timezone = reception_timezone
                        if reception_venue_name:
                            reception_event.venue_name = reception_venue_name
                        if reception_venue_address:
                            reception_event.venue_address = reception_venue_address
                        if reception_venue_phone:
                            reception_event.venue_phone = reception_venue_phone
                        if reception_google_maps_url:
                            reception_event.google_maps_url = reception_google_maps_url
                        if reception_dress_code:
                            reception_event.dress_code = reception_dress_code
                        if reception_adab_walimah:
                            reception_event.adab_walimah = reception_adab_walimah
                        if reception_special_notes:
                            reception_event.special_notes = reception_special_notes
                        if reception_venue_photo:
                            reception_event.venue_photo = reception_venue_photo
                        
                        reception_event.save()
                    except ReceptionEvent.DoesNotExist:
                        pass  # Skip if doesn't exist and required fields not complete
                
                # Invitation settings
                invitation_slug = request.POST.get('invitation_slug', '').strip()
                status = request.POST.get('status', 'draft')
                is_public = request.POST.get('is_public') == 'on'
                
                # Normalize slug: convert to lowercase and replace spaces with hyphens
                from django.utils.text import slugify
                if invitation_slug:
                    invitation_slug = slugify(invitation_slug)
                
                # Generate slug if not provided or empty after normalization
                if not invitation_slug:
                    if groom_full_name and bride_full_name:
                        groom_name = groom_nickname or groom_full_name.split()[0] if groom_full_name else 'groom'
                        bride_name = bride_nickname or bride_full_name.split()[0] if bride_full_name else 'bride'
                        base_slug = slugify(f"{groom_name}-{bride_name}")
                        invitation_slug = base_slug
                        counter = 1
                        while Invitation.objects.filter(invitation_slug=invitation_slug).exclude(pk=invitation.pk if invitation else None).exists():
                            invitation_slug = f"{base_slug}-{counter}"
                            counter += 1
                    else:
                        invitation_slug = slugify(client.user.username)
                
                # Validate slug uniqueness
                if Invitation.objects.filter(invitation_slug=invitation_slug).exclude(pk=invitation.pk if invitation else None).exists():
                    messages.error(request, 'Slug sudah digunakan. Silakan gunakan slug lain.')
                    # Don't redirect, stay on form to show error
                else:
                    if mode == 'create':
                        invitation = Invitation.objects.create(
                            client=client,
                            invitation_slug=invitation_slug,
                            status=status,
                            is_public=is_public
                        )
                        BaseAdminController.log_admin_activity(
                            request, 'create', invitation,
                            f"Invitation '{invitation_slug}' dibuat dengan data lengkap"
                        )
                        messages.success(request, f'Invitation berhasil dibuat dengan slug: {invitation_slug}')
                        return redirect('admin_panel:invitation_list')
                    else:
                        # Edit mode: only update invitation settings
                        invitation.invitation_slug = invitation_slug
                        invitation.status = status
                        invitation.is_public = is_public
                        invitation.save()
                        
                        BaseAdminController.log_admin_activity(
                            request, 'update', invitation,
                            f"Invitation '{invitation_slug}' diupdate"
                        )
                        messages.success(request, f'Invitation berhasil diupdate dengan slug: {invitation_slug}')
                        return redirect('admin_panel:invitation_list')
        except Exception as e:
            import traceback
            logger.error(f"Error managing invitation: {str(e)}")
            logger.error(traceback.format_exc())
            messages.error(request, f'Error: {str(e)}')
            # Don't redirect on error, stay on form to show error message
            # return redirect('admin_panel:invitation_add')
    
    # For edit mode, get existing data
    client_data = None
    groom_data = None
    bride_data = None
    main_event_data = None
    reception_event_data = None
    form_is_complete = False
    
    if invitation:
        client_data = invitation.client
        groom_data = GroomInfo.objects.filter(client=invitation.client).first()
        bride_data = BrideInfo.objects.filter(client=invitation.client).first()
        main_event_data = MainEvent.objects.filter(client=invitation.client).first()
        reception_event_data = ReceptionEvent.objects.filter(client=invitation.client).first()
        
        # Check if form is complete
        has_groom = groom_data is not None and groom_data.full_name
        has_bride = bride_data is not None and bride_data.full_name
        has_main_event = (
            main_event_data is not None and 
            main_event_data.event_date and 
            main_event_data.start_time and 
            main_event_data.venue_name and 
            main_event_data.venue_address
        )
        form_is_complete = has_groom and has_bride and has_main_event
    
    # Get all clients for dropdown (only in create mode)
    clients = ClientProfile.objects.all().select_related('user').order_by('user__username') if mode == 'create' else []
    
    context = {
        'invitation': invitation,
        'mode': mode,
        'clients': clients,
        'client_data': client_data,
        'groom_data': groom_data,
        'bride_data': bride_data,
        'main_event_data': main_event_data,
        'reception_event_data': reception_event_data,
        'form_is_complete': form_is_complete,
    }
    
    return render(request, 'admin_panel/invitations/invitation_form.html', context)


@login_required
@user_passes_test(lambda u: u.is_staff or u.is_superuser)
def invitation_preview(request, slug):
    """Preview invitation dengan template menggunakan slug"""
    invitation = get_object_or_404(Invitation, invitation_slug=slug)
    
    # Use the render_invitation function from invitation_templates views
    from invitation_templates.views import render_invitation
    
    # Set preview mode
    request._is_preview_mode = True
    
    # Render invitation using slug directly
    try:
        return render_invitation(request, slug, guest_slug=None)
    except Exception as e:
        logger.error(f"Error previewing invitation: {str(e)}")
        messages.error(request, f'Error preview: {str(e)}')
        return redirect('admin_panel:invitation_list')


@require_POST
@login_required
@csrf_exempt
def invitation_delete(request, pk):
    """
    Delete invitation - Always returns JSON
    
    Permission logic:
    - Admin/staff: Can delete ANY invitation
    - Regular users: Can only delete invitations they created (via ActivityLog check)
    - Users cannot delete invitations created by admin
    """
    try:
        invitation = get_object_or_404(Invitation, pk=pk)
        invitation_slug = invitation.invitation_slug
        
        # Check if user is admin/staff - they can delete any invitation
        is_admin = request.user.is_staff or request.user.is_superuser
        
        if not is_admin:
            # For regular users, check if they created this invitation
            # We check ActivityLog to see who created this invitation
            from .models import ActivityLog
            from django.contrib.contenttypes.models import ContentType
            
            invitation_ct = ContentType.objects.get_for_model(Invitation)
            creation_log = ActivityLog.objects.filter(
                target_content_type=invitation_ct,
                target_object_id=invitation.pk,
                action_type='create'
            ).order_by('-timestamp').first()
            
            # If invitation was created by admin, regular user cannot delete
            if creation_log and creation_log.actor:
                if creation_log.actor.is_staff or creation_log.actor.is_superuser:
                    return JsonResponse({
                        'status': 'error', 
                        'message': 'Anda tidak memiliki izin untuk menghapus undangan yang dibuat oleh admin.'
                    }, status=403)
                # If invitation was created by another user, cannot delete
                elif creation_log.actor != request.user:
                    return JsonResponse({
                        'status': 'error', 
                        'message': 'Anda tidak memiliki izin untuk menghapus undangan ini.'
                    }, status=403)
        
        BaseAdminController.log_admin_activity(
            request, 'delete', invitation,
            f"Invitation '{invitation_slug}' dihapus"
        )
        
        # Delete invitation (this will NOT delete the user/client, only the invitation)
        invitation.delete()
        
        # Always return JSON with proper content type
        response = JsonResponse({'status': 'success', 'message': 'Invitation berhasil dihapus'})
        response['Content-Type'] = 'application/json'
        return response
    
    except Invitation.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Invitation tidak ditemukan'}, status=404)
    
    except Exception as e:
        import traceback
        logger.error(f"Error deleting invitation: {str(e)}")
        logger.error(traceback.format_exc())
        return JsonResponse({'status': 'error', 'message': f'Error: {str(e)}'}, status=500)


# ===== INVITATION TEMPLATES VIEWS =====

# ===== TEMPLATE ASSETS VIEWS ===== (REMOVED - not needed for small website)
# category_list, music_library_list, theme_rating_list, background_asset_list, quote_library_list


# ===== AJAX ENDPOINTS =====
# Note: ajax_add_category removed - using hardcoded categories instead
