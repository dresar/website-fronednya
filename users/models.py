from django.db import models
from django.contrib.auth.models import User
from django_summernote.fields import SummernoteTextField
from PIL import Image
import os
import uuid

# Create your models here.

class ClientProfile(models.Model):
    """Profile Extend User untuk Data Klien"""
    SUBSCRIPTION_CHOICES = [
        ('free', 'Free'),
        ('premium', 'Premium'),
        ('gold', 'Gold'),
        ('platinum', 'Platinum'),
    ]
    
    ACCOUNT_LEVEL_CHOICES = [
        ('trial', 'Trial'),
        ('basic', 'Basic'),
        ('pro', 'Pro'),
        ('enterprise', 'Enterprise'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, verbose_name="User")
    phone_number = models.CharField(max_length=20, verbose_name="Nomor HP")
    whatsapp_number = models.CharField(max_length=20, verbose_name="Nomor WhatsApp")
    subscription_type = models.CharField(max_length=20, choices=SUBSCRIPTION_CHOICES, default='free', verbose_name="Tipe Langganan")
    account_level = models.CharField(max_length=20, choices=ACCOUNT_LEVEL_CHOICES, default='trial', verbose_name="Level Akun")
    subscription_expires = models.DateTimeField(blank=True, null=True, verbose_name="Berakhir Langganan")
    profile_photo = models.ImageField(upload_to='client_profiles/', blank=True, null=True, verbose_name="Foto Profil")
    address = models.TextField(blank=True, verbose_name="Alamat")
    city = models.CharField(max_length=100, blank=True, verbose_name="Kota")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Dibuat Pada")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Diupdate Pada")
    
    def __str__(self):
        return f"{self.user.username} - {self.subscription_type}"
        
    class Meta:
        verbose_name = "Profile Klien"
        verbose_name_plural = "Profile Klien"


class GroomInfo(models.Model):
    """Data Detail Mempelai Pria"""
    client = models.OneToOneField(ClientProfile, on_delete=models.CASCADE, verbose_name="Klien")
    full_name = models.CharField(max_length=200, verbose_name="Nama Lengkap")
    nickname = models.CharField(max_length=100, blank=True, verbose_name="Nama Panggilan")
    father_name = models.CharField(max_length=200, blank=True, verbose_name="Nama Ayah")
    mother_name = models.CharField(max_length=200, blank=True, verbose_name="Nama Ibu")
    child_order = models.CharField(max_length=100, blank=True, verbose_name="Putra/Putri Ke-", help_text="Contoh: Putra pertama dari")
    main_photo = models.ImageField(upload_to='groom_photos/', blank=True, null=True, verbose_name="Foto Utama")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Dibuat Pada")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Diupdate Pada")
    
    def __str__(self):
        return f"Mempelai Pria - {self.full_name}"
        
    class Meta:
        verbose_name = "Data Mempelai Pria"
        verbose_name_plural = "Data Mempelai Pria"


class BrideInfo(models.Model):
    """Data Detail Mempelai Wanita"""
    client = models.OneToOneField(ClientProfile, on_delete=models.CASCADE, verbose_name="Klien")
    full_name = models.CharField(max_length=200, verbose_name="Nama Lengkap")
    nickname = models.CharField(max_length=100, blank=True, verbose_name="Nama Panggilan")
    father_name = models.CharField(max_length=200, blank=True, verbose_name="Nama Ayah")
    mother_name = models.CharField(max_length=200, blank=True, verbose_name="Nama Ibu")
    child_order = models.CharField(max_length=100, blank=True, verbose_name="Putra/Putri Ke-", help_text="Contoh: Putri pertama dari")
    main_photo = models.ImageField(upload_to='bride_photos/', blank=True, null=True, verbose_name="Foto Utama")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Dibuat Pada")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Diupdate Pada")
    
    def __str__(self):
        return f"Mempelai Wanita - {self.full_name}"
        
    class Meta:
        verbose_name = "Data Mempelai Wanita"
        verbose_name_plural = "Data Mempelai Wanita"


class MainEvent(models.Model):
    """Data Acara Utama (Akad/Pemberkatan)"""
    TIMEZONE_CHOICES = [
        ('WIB', 'Waktu Indonesia Barat (WIB)'),
        ('WITA', 'Waktu Indonesia Tengah (WITA)'),
        ('WIT', 'Waktu Indonesia Timur (WIT)'),
    ]
    
    client = models.OneToOneField(ClientProfile, on_delete=models.CASCADE, verbose_name="Klien")
    event_name = models.CharField(max_length=100, default="Akad Nikah", verbose_name="Nama Acara")
    event_date = models.DateField(verbose_name="Tanggal Acara")
    start_time = models.TimeField(verbose_name="Jam Mulai")
    end_time = models.TimeField(blank=True, null=True, verbose_name="Jam Selesai")
    timezone = models.CharField(max_length=10, choices=TIMEZONE_CHOICES, default='WIB', verbose_name="Zona Waktu")
    venue_name = models.CharField(max_length=200, verbose_name="Nama Tempat")
    venue_address = models.TextField(verbose_name="Alamat Lengkap")
    venue_phone = models.CharField(max_length=20, blank=True, verbose_name="No Telp Tempat")
    google_maps_url = models.URLField(max_length=500, blank=True, verbose_name="Link Google Maps")
    venue_photo = models.ImageField(upload_to='venue_photos/', blank=True, null=True, verbose_name="Foto Tempat")
    special_notes = models.TextField(blank=True, verbose_name="Catatan Khusus")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Dibuat Pada")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Diupdate Pada")
    
    def __str__(self):
        return f"{self.event_name} - {self.client.user.username}"
        
    class Meta:
        verbose_name = "Acara Utama"
        verbose_name_plural = "Acara Utama"


class ReceptionEvent(models.Model):
    """Data Acara Resepsi"""
    TIMEZONE_CHOICES = [
        ('WIB', 'Waktu Indonesia Barat (WIB)'),
        ('WITA', 'Waktu Indonesia Tengah (WITA)'),
        ('WIT', 'Waktu Indonesia Timur (WIT)'),
    ]
    
    client = models.OneToOneField(ClientProfile, on_delete=models.CASCADE, verbose_name="Klien")
    event_name = models.CharField(max_length=100, default="Resepsi Pernikahan", verbose_name="Nama Acara")
    event_date = models.DateField(verbose_name="Tanggal Resepsi")
    start_time = models.TimeField(verbose_name="Jam Mulai")
    end_time = models.TimeField(blank=True, null=True, verbose_name="Jam Selesai")
    timezone = models.CharField(max_length=10, choices=TIMEZONE_CHOICES, default='WIB', verbose_name="Zona Waktu")
    venue_name = models.CharField(max_length=200, verbose_name="Nama Tempat")
    venue_address = models.TextField(verbose_name="Alamat Lengkap")
    venue_phone = models.CharField(max_length=20, blank=True, verbose_name="No Telp Tempat")
    google_maps_url = models.URLField(max_length=500, blank=True, verbose_name="Link Google Maps")
    venue_photo = models.ImageField(upload_to='venue_photos/', blank=True, null=True, verbose_name="Foto Tempat")
    dress_code = models.CharField(max_length=100, blank=True, verbose_name="Dress Code")
    adab_walimah = models.TextField(blank=True, verbose_name="Adab Walimah", help_text="Panduan adab untuk tamu undangan")
    special_notes = models.TextField(blank=True, verbose_name="Catatan Khusus")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Dibuat Pada")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Diupdate Pada")
    
    def __str__(self):
        return f"{self.event_name} - {self.client.user.username}"
        
    class Meta:
        verbose_name = "Acara Resepsi"
        verbose_name_plural = "Acara Resepsi"


class PhotoGallery(models.Model):
    """Galeri Foto Memorable Moment"""
    client = models.ForeignKey(ClientProfile, on_delete=models.CASCADE, verbose_name="Klien")
    title = models.CharField(max_length=200, blank=True, verbose_name="Judul Foto")
    photo = models.ImageField(upload_to='photo_gallery/', verbose_name="Foto")
    caption = models.TextField(blank=True, verbose_name="Keterangan")
    order = models.PositiveIntegerField(default=0, verbose_name="Urutan")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Dibuat Pada")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Diupdate Pada")
    
    def __str__(self):
        return f"{self.title or 'Foto'} - {self.client.user.username}"
        
    class Meta:
        verbose_name = "Galeri Foto"
        verbose_name_plural = "Galeri Foto"
        ordering = ['order', '-created_at']


class LoveStory(models.Model):
    """Our Story - Timeline Cerita Cinta"""
    client = models.ForeignKey(ClientProfile, on_delete=models.CASCADE, verbose_name="Klien")
    title = models.CharField(max_length=200, verbose_name="Judul Cerita")
    story_date = models.DateField(verbose_name="Tanggal Peristiwa")
    story_content = SummernoteTextField(verbose_name="Isi Cerita")
    story_photo = models.ImageField(upload_to='love_story/', blank=True, null=True, verbose_name="Foto Pendukung")
    order = models.PositiveIntegerField(default=0, verbose_name="Urutan")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Dibuat Pada")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Diupdate Pada")
    
    def __str__(self):
        return f"{self.title} - {self.client.user.username}"
        
    class Meta:
        verbose_name = "Cerita Cinta"
        verbose_name_plural = "Cerita Cinta"
        ordering = ['order', 'story_date']


class Invitation(models.Model):
    """Model untuk Undangan Digital"""
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('active', 'Aktif'),
        ('inactive', 'Nonaktif'),
    ]
    
    client = models.OneToOneField(ClientProfile, on_delete=models.CASCADE, verbose_name="Klien", related_name='invitation')
    invitation_slug = models.SlugField(max_length=200, unique=True, verbose_name="Slug Undangan", help_text="URL unik untuk undangan (contoh: romeo-juliet)")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft', verbose_name="Status")
    is_public = models.BooleanField(default=True, verbose_name="Publik", help_text="Apakah undangan bisa diakses publik tanpa login")
    view_count = models.PositiveIntegerField(default=0, verbose_name="Jumlah Dilihat")
    last_viewed_at = models.DateTimeField(blank=True, null=True, verbose_name="Terakhir Dilihat")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Dibuat Pada")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Diupdate Pada")
    
    def __str__(self):
        return f"Undangan: {self.invitation_slug} - {self.client.user.username}"
    
    def save(self, *args, **kwargs):
        if not self.invitation_slug:
            # Generate slug from groom and bride names
            groom = GroomInfo.objects.filter(client=self.client).first()
            bride = BrideInfo.objects.filter(client=self.client).first()
            
            if groom and bride:
                # Use nicknames if available, otherwise full names
                groom_name = groom.nickname or groom.full_name.split()[0] if groom.full_name else 'groom'
                bride_name = bride.nickname or bride.full_name.split()[0] if bride.full_name else 'bride'
                base_slug = f"{groom_name}-{bride_name}".lower()
            else:
                # Fallback to username
                base_slug = self.client.user.username.lower()
            
            # Make slug unique
            from django.utils.text import slugify
            base_slug = slugify(base_slug)
            unique_slug = base_slug
            counter = 1
            while Invitation.objects.filter(invitation_slug=unique_slug).exists():
                unique_slug = f"{base_slug}-{counter}"
                counter += 1
            
            self.invitation_slug = unique_slug
        
        super().save(*args, **kwargs)
    
    class Meta:
        verbose_name = "Undangan"
        verbose_name_plural = "Undangan"
        ordering = ['-created_at']


class InvitationWish(models.Model):
    """Wishes/Ucapan dari Tamu untuk Undangan Real"""
    invitation = models.ForeignKey(Invitation, on_delete=models.CASCADE, related_name='wishes', verbose_name="Undangan")
    name = models.CharField(max_length=200, verbose_name="Nama Pengirim")
    address = models.CharField(max_length=500, blank=True, verbose_name="Alamat")
    comment = models.TextField(verbose_name="Ucapan/Doa")
    image = models.ImageField(upload_to='wishes_images/', blank=True, null=True, verbose_name="Gambar")
    is_approved = models.BooleanField(default=True, verbose_name="Disetujui")
    ip_address = models.GenericIPAddressField(blank=True, null=True, verbose_name="IP Address")
    submitted_at = models.DateTimeField(auto_now_add=True, verbose_name="Dikirim Pada")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Dibuat Pada")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Diupdate Pada")
    
    def __str__(self):
        return f"Ucapan dari {self.name} - {self.invitation.invitation_slug}"
    
    class Meta:
        verbose_name = "Ucapan Undangan"
        verbose_name_plural = "Ucapan Undangan"
        ordering = ['-submitted_at']


