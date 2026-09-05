from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.utils import timezone
from datetime import datetime, timedelta

from .models import (
    ClientProfile, GroomInfo, BrideInfo, MainEvent, ReceptionEvent,
    PhotoGallery, LoveStory
)
from .forms import (
    ClientProfileForm, GroomInfoForm, BrideInfoForm,
    MainEventForm, ReceptionEventForm
)
try:
    from qr_manager.models import Guest, RSVPResponse, GuestWishes
except ImportError:
    # Fallback if qr_manager models not available
    Guest = None
    RSVPResponse = None
    GuestWishes = None


def user_login(request):
    """User login view"""
    if request.user.is_authenticated:
        return redirect('users:dashboard')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        remember = request.POST.get('remember')
        
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            if not remember:
                request.session.set_expiry(0)  # Session expires when browser closes
            messages.success(request, f'Selamat datang, {user.username}!')
            return redirect('users:dashboard')
        else:
            messages.error(request, 'Username atau password salah.')
    
    return render(request, 'users/login.html')




def user_logout(request):
    """User logout view"""
    logout(request)
    messages.success(request, 'Anda telah berhasil logout.')
    return redirect('users:login')


def user_register(request):
    """User registration view - Now redirects to login page with register tab"""
    if request.user.is_authenticated:
        return redirect('users:dashboard')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        password_confirm = request.POST.get('password_confirm')
        
        if password != password_confirm:
            messages.error(request, 'Password tidak cocok.')
        elif len(password) < 8:
            messages.error(request, 'Password minimal 8 karakter.')
        else:
            from django.contrib.auth.models import User
            if User.objects.filter(username=username).exists():
                messages.error(request, 'Username sudah digunakan.')
            elif User.objects.filter(email=email).exists():
                messages.error(request, 'Email sudah terdaftar.')
            else:
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    password=password
                )
                # Create ClientProfile
                ClientProfile.objects.create(
                    user=user,
                    phone_number=request.POST.get('phone_number', ''),
                    whatsapp_number=request.POST.get('whatsapp_number', ''),
                    subscription_type='free',
                    account_level='trial'
                )
                messages.success(request, 'Registrasi berhasil! Silakan login.')
                return redirect('users:login')
    
    # Redirect to login page with register tab active
    return redirect('users:login?register=true')


@login_required
def dashboard(request):
    """User dashboard view"""
    try:
        client_profile = ClientProfile.objects.get(user=request.user)
    except ClientProfile.DoesNotExist:
        client_profile = ClientProfile.objects.create(
            user=request.user,
            phone_number='',
            whatsapp_number='',
            subscription_type='free',
            account_level='trial'
        )
    
    # Get statistics
    guests = Guest.objects.filter(client=client_profile) if Guest else []
    rsvp_responses = RSVPResponse.objects.filter(guest__client=client_profile) if RSVPResponse else []
    guest_wishes = GuestWishes.objects.filter(guest__client=client_profile) if GuestWishes else []
    main_event = MainEvent.objects.filter(client=client_profile).first()
    
    if isinstance(guests, list):
        stats = {
            'total_guests': len(guests),
            'attending_guests': 0,
            'total_wishes': len(guest_wishes),
        }
    else:
        stats = {
            'total_guests': guests.count(),
            'attending_guests': rsvp_responses.filter(attendance_status='attending').count() if rsvp_responses else 0,
            'total_wishes': guest_wishes.count() if guest_wishes else 0,
        }
    
    # Calculate days until event
    if main_event and main_event.event_date:
        today = timezone.now().date()
        event_date = main_event.event_date
        if event_date > today:
            stats['days_until_event'] = (event_date - today).days
        else:
            stats['days_until_event'] = 0
    else:
        stats['days_until_event'] = None
    
    # Recent activities
    recent_activities = []
    if rsvp_responses:
        recent_rsvp = rsvp_responses.order_by('-created_at')[:5] if hasattr(rsvp_responses, 'order_by') else rsvp_responses[:5]
        for rsvp in recent_rsvp:
            recent_activities.append({
                'guest_name': rsvp.guest.full_name,
                'activity_text': f'Mengkonfirmasi kehadiran',
                'timestamp': rsvp.created_at
            })
    
    if guest_wishes:
        recent_wishes = guest_wishes.order_by('-created_at')[:5] if hasattr(guest_wishes, 'order_by') else guest_wishes[:5]
        for wish in recent_wishes:
            recent_activities.append({
                'guest_name': wish.guest.full_name,
                'activity_text': 'Mengirim ucapan',
                'timestamp': wish.created_at
            })
    
    recent_activities.sort(key=lambda x: x['timestamp'], reverse=True)
    recent_activities = recent_activities[:5]
    
    context = {
        'user': request.user,
        'client_profile': client_profile,
        'stats': stats,
        'main_event': main_event,
        'recent_activities': recent_activities,
    }
    
    return render(request, 'users/dashboard.html', context)


@login_required
def wedding_data_form(request):
    """Wedding data form view with step-by-step wizard"""
    try:
        client_profile = ClientProfile.objects.get(user=request.user)
    except ClientProfile.DoesNotExist:
        client_profile = ClientProfile.objects.create(
            user=request.user,
            phone_number='',
            whatsapp_number='',
            subscription_type='free',
            account_level='trial'
        )
    
    groom_info = GroomInfo.objects.filter(client=client_profile).first()
    bride_info = BrideInfo.objects.filter(client=client_profile).first()
    main_event = MainEvent.objects.filter(client=client_profile).first()
    reception_event = ReceptionEvent.objects.filter(client=client_profile).first()
    
    if request.method == 'POST':
        try:
            # Step 1: Groom Info
            groom_full_name = request.POST.get('groom_full_name', '').strip()
            groom_nickname = request.POST.get('groom_nickname', '').strip()
            groom_father_name = request.POST.get('groom_father_name', '').strip()
            groom_mother_name = request.POST.get('groom_mother_name', '').strip()
            groom_child_order = request.POST.get('groom_child_order', '').strip()
            groom_main_photo = request.FILES.get('groom_main_photo')
            
            if groom_full_name:
                if groom_info:
                    groom_info.full_name = groom_full_name
                    groom_info.nickname = groom_nickname
                    groom_info.father_name = groom_father_name
                    groom_info.mother_name = groom_mother_name
                    groom_info.child_order = groom_child_order
                    if groom_main_photo:
                        groom_info.main_photo = groom_main_photo
                    groom_info.save()
                else:
                    groom_info = GroomInfo.objects.create(
                        client=client_profile,
                        full_name=groom_full_name,
                        nickname=groom_nickname,
                        father_name=groom_father_name,
                        mother_name=groom_mother_name,
                        child_order=groom_child_order,
                        main_photo=groom_main_photo if groom_main_photo else None
                    )
            
            # Step 2: Bride Info
            bride_full_name = request.POST.get('bride_full_name', '').strip()
            bride_nickname = request.POST.get('bride_nickname', '').strip()
            bride_father_name = request.POST.get('bride_father_name', '').strip()
            bride_mother_name = request.POST.get('bride_mother_name', '').strip()
            bride_child_order = request.POST.get('bride_child_order', '').strip()
            bride_main_photo = request.FILES.get('bride_main_photo')
            
            if bride_full_name:
                if bride_info:
                    bride_info.full_name = bride_full_name
                    bride_info.nickname = bride_nickname
                    bride_info.father_name = bride_father_name
                    bride_info.mother_name = bride_mother_name
                    bride_info.child_order = bride_child_order
                    if bride_main_photo:
                        bride_info.main_photo = bride_main_photo
                    bride_info.save()
                else:
                    bride_info = BrideInfo.objects.create(
                        client=client_profile,
                        full_name=bride_full_name,
                        nickname=bride_nickname,
                        father_name=bride_father_name,
                        mother_name=bride_mother_name,
                        child_order=bride_child_order,
                        main_photo=bride_main_photo if bride_main_photo else None
                    )
            
            # Step 3: Main Event (Akad)
            main_event_date = request.POST.get('main_event_date')
            main_start_time = request.POST.get('main_start_time')
            main_venue_name = request.POST.get('main_venue_name', '').strip()
            main_venue_address = request.POST.get('main_venue_address', '').strip()
            main_google_maps_url = request.POST.get('main_google_maps_url', '').strip()
            main_event_name = request.POST.get('main_event_name', 'Akad Nikah').strip()
            
            if main_event_date and main_start_time and main_venue_name and main_venue_address:
                if main_event:
                    main_event.event_name = main_event_name
                    main_event.event_date = main_event_date
                    main_event.start_time = main_start_time
                    main_event.venue_name = main_venue_name
                    main_event.venue_address = main_venue_address
                    main_event.google_maps_url = main_google_maps_url
                    main_event.save()
                else:
                    MainEvent.objects.create(
                        client=client_profile,
                        event_name=main_event_name,
                        event_date=main_event_date,
                        start_time=main_start_time,
                        venue_name=main_venue_name,
                        venue_address=main_venue_address,
                        google_maps_url=main_google_maps_url
                    )
            
            # Step 3: Reception Event
            reception_event_date = request.POST.get('reception_event_date', '').strip()
            reception_start_time = request.POST.get('reception_start_time', '').strip()
            reception_venue_name = request.POST.get('reception_venue_name', '').strip()
            reception_venue_address = request.POST.get('reception_venue_address', '').strip()
            reception_google_maps_url = request.POST.get('reception_google_maps_url', '').strip()
            reception_event_name = request.POST.get('reception_event_name', 'Resepsi Pernikahan').strip()
            reception_dress_code = request.POST.get('reception_dress_code', '').strip()
            reception_adab_walimah = request.POST.get('reception_adab_walimah', '').strip()
            
            if reception_event_date and reception_start_time and reception_venue_name and reception_venue_address:
                if reception_event:
                    reception_event.event_name = reception_event_name
                    reception_event.event_date = reception_event_date
                    reception_event.start_time = reception_start_time
                    reception_event.venue_name = reception_venue_name
                    reception_event.venue_address = reception_venue_address
                    reception_event.google_maps_url = reception_google_maps_url
                    reception_event.dress_code = reception_dress_code
                    reception_event.adab_walimah = reception_adab_walimah
                    reception_event.save()
                else:
                    ReceptionEvent.objects.create(
                        client=client_profile,
                        event_name=reception_event_name,
                        event_date=reception_event_date,
                        start_time=reception_start_time,
                        venue_name=reception_venue_name,
                        venue_address=reception_venue_address,
                        google_maps_url=reception_google_maps_url,
                        dress_code=reception_dress_code,
                        adab_walimah=reception_adab_walimah
                    )
            
            # Handle Photo Gallery (Memorable Moment)
            # Save existing photos with file paths before delete
            existing_photos_data = []
            for photo in PhotoGallery.objects.filter(client=client_profile).order_by('order'):
                existing_photos_data.append({
                    'title': photo.title,
                    'caption': photo.caption,
                    'photo_path': photo.photo.name if photo.photo else None,
                    'photo_file': photo.photo  # Keep reference to file
                })
            
            # Clear existing photos
            PhotoGallery.objects.filter(client=client_profile).delete()
            
            photo_titles = request.POST.getlist('photo_title[]')
            photo_captions = request.POST.getlist('photo_caption[]')
            photo_files = request.FILES.getlist('photo_files[]')
            
            # Process all items
            max_items = max(len(photo_titles), len(photo_files)) if photo_titles or photo_files else 0
            for idx in range(max_items):
                photo_title = photo_titles[idx] if idx < len(photo_titles) else ''
                photo_caption = photo_captions[idx] if idx < len(photo_captions) else ''
                photo_file = photo_files[idx] if idx < len(photo_files) else None
                
                # Use existing photo if no new file uploaded
                photo_to_save = photo_file
                if not photo_file and idx < len(existing_photos_data) and existing_photos_data[idx]['photo_file']:
                    # Copy existing photo file
                    from django.core.files.base import ContentFile
                    from django.core.files.storage import default_storage
                    existing_photo = existing_photos_data[idx]['photo_file']
                    if existing_photo and existing_photo.name:
                        # Read existing file and save as new
                        try:
                            with existing_photo.open('rb') as f:
                                photo_to_save = ContentFile(f.read(), name=existing_photo.name)
                        except:
                            photo_to_save = None
                
                # Only create if there's a file or title
                if photo_to_save or photo_title.strip():
                    PhotoGallery.objects.create(
                        client=client_profile,
                        title=photo_title.strip(),
                        photo=photo_to_save,
                        caption=photo_caption.strip(),
                        order=idx
                    )
            
            # Handle Love Story (Our Story)
            # Save existing stories with file paths before delete
            existing_stories_data = []
            for story in LoveStory.objects.filter(client=client_profile).order_by('order'):
                existing_stories_data.append({
                    'title': story.title,
                    'story_date': story.story_date,
                    'story_content': story.story_content,
                    'photo_path': story.story_photo.name if story.story_photo else None,
                    'photo_file': story.story_photo  # Keep reference to file
                })
            
            # Clear existing stories
            LoveStory.objects.filter(client=client_profile).delete()
            
            story_titles = request.POST.getlist('story_title[]')
            story_dates = request.POST.getlist('story_date[]')
            story_contents = request.POST.getlist('story_content[]')
            story_photos = request.FILES.getlist('story_photo[]')
            
            for idx, story_title in enumerate(story_titles):
                if story_title and story_title.strip():
                    story_date_str = story_dates[idx] if idx < len(story_dates) and story_dates[idx] else None
                    story_content = story_contents[idx] if idx < len(story_contents) else ''
                    story_photo = story_photos[idx] if idx < len(story_photos) and story_photos[idx] else None
                    
                    # Use existing photo if no new file uploaded
                    photo_to_save = story_photo
                    if not story_photo and idx < len(existing_stories_data) and existing_stories_data[idx]['photo_file']:
                        # Copy existing photo file
                        from django.core.files.base import ContentFile
                        existing_photo = existing_stories_data[idx]['photo_file']
                        if existing_photo and existing_photo.name:
                            try:
                                with existing_photo.open('rb') as f:
                                    photo_to_save = ContentFile(f.read(), name=existing_photo.name)
                            except:
                                photo_to_save = None
                    
                    # Use existing date if no new date provided
                    if not story_date_str and idx < len(existing_stories_data) and existing_stories_data[idx]['story_date']:
                        story_date_obj = existing_stories_data[idx]['story_date']
                    else:
                        # Parse date string to date object
                        from datetime import datetime
                        if story_date_str and story_date_str.strip():
                            try:
                                story_date_obj = datetime.strptime(story_date_str.strip(), '%Y-%m-%d').date()
                            except (ValueError, TypeError):
                                story_date_obj = timezone.now().date()
                        else:
                            story_date_obj = timezone.now().date()
                    
                    # Use existing content if no new content provided
                    content_to_save = story_content if story_content.strip() else (existing_stories_data[idx]['story_content'] if idx < len(existing_stories_data) else '')
                    
                    LoveStory.objects.create(
                        client=client_profile,
                        title=story_title.strip(),
                        story_date=story_date_obj,
                        story_content=content_to_save,
                        story_photo=photo_to_save,
                        order=idx
                    )
            
            messages.success(request, 'Data berhasil disimpan!')
            return redirect('users:wedding_data_form')
        except Exception as e:
            import traceback
            messages.error(request, f'Error menyimpan data: {str(e)}')
            print(f"Error: {str(e)}")
            print(traceback.format_exc())
    
    # Refresh data after POST
    groom_info = GroomInfo.objects.filter(client=client_profile).first()
    bride_info = BrideInfo.objects.filter(client=client_profile).first()
    main_event = MainEvent.objects.filter(client=client_profile).first()
    reception_event = ReceptionEvent.objects.filter(client=client_profile).first()
    photo_gallery = PhotoGallery.objects.filter(client=client_profile).order_by('order', '-created_at')
    love_stories = LoveStory.objects.filter(client=client_profile).order_by('order', 'story_date')
    
    # Check if data is complete (for read-only mode)
    is_complete = bool(groom_info and bride_info and main_event and reception_event)
    
    # Check if edit mode is requested
    edit_mode = request.GET.get('edit', 'false').lower() == 'true'
    
    # If data is complete and not in edit mode, show read-only view
    if is_complete and not edit_mode:
        context = {
            'client_profile': client_profile,
            'groom_info': groom_info,
            'bride_info': bride_info,
            'main_event': main_event,
            'reception_event': reception_event,
            'photo_gallery': photo_gallery,
            'love_stories': love_stories,
            'is_complete': True,
            'edit_mode': False,
        }
        return render(request, 'users/wedding_data_view.html', context)
    
    # Edit mode or incomplete data - show form
    context = {
        'client_profile': client_profile,
        'groom_info': groom_info,
        'bride_info': bride_info,
        'main_event': main_event,
        'reception_event': reception_event,
        'photo_gallery': photo_gallery,
        'love_stories': love_stories,
        'is_complete': is_complete,
        'edit_mode': True,
    }
    
    return render(request, 'users/wedding_data_form.html', context)


@login_required
def guest_manager(request):
    """Guest management view"""
    client_profile = get_object_or_404(ClientProfile, user=request.user)
    if not Guest:
        guests = []
    else:
        guests = Guest.objects.filter(client=client_profile).order_by('-created_at')
    
    context = {
        'client_profile': client_profile,
        'guests': guests,
    }
    
    return render(request, 'users/guest_manager.html', context)


@login_required
def add_guest(request):
    """Add new guest"""
    if not Guest:
        messages.error(request, 'Fitur Guest Manager belum tersedia.')
        return redirect('users:guest_manager')
    
    client_profile = get_object_or_404(ClientProfile, user=request.user)
    
    if request.method == 'POST':
        name = request.POST.get('guest_name')
        phone = request.POST.get('guest_phone', '')
        email = request.POST.get('guest_email', '')
        
        if name:
            guest = Guest.objects.create(
                client=client_profile,
                full_name=name,
                phone_number=phone,
                email=email
            )
            messages.success(request, f'Tamu {name} berhasil ditambahkan!')
        else:
            messages.error(request, 'Nama tamu wajib diisi.')
    
    return redirect('users:guest_manager')


@login_required
def edit_guest(request, pk):
    """Edit guest"""
    if not Guest:
        messages.error(request, 'Fitur Guest Manager belum tersedia.')
        return redirect('users:guest_manager')
    
    client_profile = get_object_or_404(ClientProfile, user=request.user)
    guest = get_object_or_404(Guest, pk=pk, client=client_profile)
    
    if request.method == 'POST':
        guest.full_name = request.POST.get('guest_name', guest.full_name)
        guest.phone_number = request.POST.get('guest_phone', guest.phone_number)
        guest.email = request.POST.get('guest_email', guest.email)
        guest.save()
        messages.success(request, 'Data tamu berhasil diupdate!')
        return redirect('users:guest_manager')
    
    return render(request, 'users/edit_guest.html', {'guest': guest})


@login_required
def delete_guest(request, pk):
    """Delete guest"""
    if not Guest:
        messages.error(request, 'Fitur Guest Manager belum tersedia.')
        return redirect('users:guest_manager')
    
    client_profile = get_object_or_404(ClientProfile, user=request.user)
    guest = get_object_or_404(Guest, pk=pk, client=client_profile)
    
    if request.method == 'POST':
        guest_name = guest.full_name
        guest.delete()
        messages.success(request, f'Tamu {guest_name} berhasil dihapus!')
    
    return redirect('users:guest_manager')


@login_required
def rsvp_feed(request):
    """RSVP feed view"""
    client_profile = get_object_or_404(ClientProfile, user=request.user)
    
    if RSVPResponse:
        rsvp_responses = RSVPResponse.objects.filter(
            guest__client=client_profile
        ).order_by('-created_at')
    else:
        rsvp_responses = []
    
    if GuestWishes:
        guest_wishes = GuestWishes.objects.filter(
            guest__client=client_profile
        ).order_by('-created_at')
    else:
        guest_wishes = []
    
    context = {
        'client_profile': client_profile,
        'rsvp_responses': rsvp_responses,
        'guest_wishes': guest_wishes,
    }
    
    return render(request, 'users/rsvp_feed.html', context)


@login_required
def profile(request):
    """User profile view - REMOVED (Theme model deleted)"""
    client_profile = get_object_or_404(ClientProfile, user=request.user)
    messages.info(request, 'Fitur pemilihan tema telah dinonaktifkan karena model Theme telah dihapus.')
    
    context = {
        'user': request.user,
        'client_profile': client_profile,
    }
    
    return render(request, 'users/profile.html', context)


@login_required
def select_theme(request):
    """Select theme for invitation - REMOVED (Theme model deleted)"""
    messages.error(request, 'Fitur pemilihan tema telah dinonaktifkan karena model Theme telah dihapus.')
    return redirect('users:profile')


@login_required
def search_themes(request):
    """AJAX endpoint untuk search themes - REMOVED (Theme model deleted)"""
    from django.http import JsonResponse
    return JsonResponse({'themes': [], 'message': 'Fitur pencarian tema telah dinonaktifkan karena model Theme telah dihapus.'})


@login_required
def change_password(request):
    """Change password view"""
    if request.method == 'POST':
        old_password = request.POST.get('old_password')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')
        
        if not request.user.check_password(old_password):
            messages.error(request, 'Password lama salah.')
        elif new_password != confirm_password:
            messages.error(request, 'Password baru tidak cocok.')
        elif len(new_password) < 8:
            messages.error(request, 'Password minimal 8 karakter.')
        else:
            request.user.set_password(new_password)
            request.user.save()
            # Update session to prevent logout after password change
            update_session_auth_hash(request, request.user)
            messages.success(request, 'Password berhasil diubah!')
            return redirect('users:profile')
    
    return render(request, 'users/change_password.html')


@login_required
def notifications(request):
    """Notifications view"""
    if request.method == 'POST':
        # Handle notification settings save
        # For now, just show success message
        # In production, you would save these settings to database
        messages.success(request, 'Pengaturan notifikasi berhasil disimpan!')
        return redirect('users:notifications')
    
    return render(request, 'users/notifications.html')


@login_required
def help(request):
    """Help view"""
    return render(request, 'users/help.html')
