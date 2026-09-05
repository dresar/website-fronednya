from django.db import models
from django.utils.text import slugify
from django.contrib.auth.models import User
from django_summernote.fields import SummernoteTextField
from users.models import ClientProfile
import qrcode
from io import BytesIO
from django.core.files import File
from PIL import Image
import uuid
from django.utils import timezone

# Create your models here.

class GuestGroup(models.Model):
    """Pengelompokan Tamu"""
    GROUP_TYPE_CHOICES = [
        ('family_bride', 'Keluarga Mempelai Wanita'),
        ('family_groom', 'Keluarga Mempelai Pria'),
        ('friends_bride', 'Teman Mempelai Wanita'),
        ('friends_groom', 'Teman Mempelai Pria'),
        ('colleagues', 'Kolega/Rekan Kerja'),
        ('neighbors', 'Tetangga'),
        ('vip', 'VIP/Penting'),
        ('children', 'Anak-anak'),
        ('elderly', 'Orang Tua/Lansia'),
        ('special_needs', 'Berkebutuhan Khusus'),
        ('vendors', 'Vendor/Pemasok'),
        ('media', 'Media/Wartawan'),
    ]
    
    client = models.ForeignKey(ClientProfile, on_delete=models.CASCADE, verbose_name="Klien")
    group_name = models.CharField(max_length=100, verbose_name="Nama Group")
    group_type = models.CharField(max_length=20, choices=GROUP_TYPE_CHOICES, verbose_name="Tipe Group")
    description = models.TextField(blank=True, verbose_name="Deskripsi")
    color_code = models.CharField(max_length=7, default="#007bff", verbose_name="Kode Warna")
    max_capacity = models.PositiveIntegerField(blank=True, null=True, verbose_name="Kapasitas Maksimal")
    special_instructions = models.TextField(blank=True, verbose_name="Instruksi Khusus")
    order = models.PositiveIntegerField(default=0, verbose_name="Urutan")
    is_active = models.BooleanField(default=True, verbose_name="Status Aktif")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Dibuat Pada")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Diupdate Pada")
    
    def __str__(self):
        return f"{self.group_name} ({self.client.user.username})"
        
    class Meta:
        verbose_name = "Group Tamu"
        verbose_name_plural = "Group Tamu"
        ordering = ['order', 'group_name']


class Guest(models.Model):
    """Data Tamu Undangan"""
    GENDER_CHOICES = [
        ('L', 'Laki-laki'),
        ('P', 'Perempuan'),
    ]
    
    AGE_GROUP_CHOICES = [
        ('child', 'Anak-anak (0-12)'),
        ('teen', 'Remaja (13-17)'),
        ('adult', 'Dewasa (18-59)'),
        ('elderly', 'Lansia (60+)'),
    ]
    
    client = models.ForeignKey(ClientProfile, on_delete=models.CASCADE, verbose_name="Klien")
    guest_group = models.ForeignKey(GuestGroup, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Group Tamu")
    full_name = models.CharField(max_length=200, verbose_name="Nama Lengkap")
    nickname = models.CharField(max_length=100, blank=True, verbose_name="Nama Panggilan")
    phone_number = models.CharField(max_length=20, blank=True, verbose_name="No HP")
    whatsapp_number = models.CharField(max_length=20, blank=True, verbose_name="No WhatsApp")
    email = models.EmailField(blank=True, verbose_name="Email")
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, blank=True, verbose_name="Jenis Kelamin")
    age_group = models.CharField(max_length=10, choices=AGE_GROUP_CHOICES, default='adult', verbose_name="Kelompok Umur")
    address = models.TextField(blank=True, verbose_name="Alamat")
    city = models.CharField(max_length=100, blank=True, verbose_name="Kota")
    companion_count = models.PositiveIntegerField(default=1, verbose_name="Jumlah Pendamping")
    slug = models.SlugField(max_length=250, unique=True, verbose_name="Slug Unik")
    profile_photo = models.ImageField(upload_to='guest_photos/', blank=True, null=True, verbose_name="Foto Profil")
    notes = models.TextField(blank=True, verbose_name="Catatan")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Dibuat Pada")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Diupdate Pada")
    
    def __str__(self):
        return f"{self.full_name} ({self.client.user.username})"
    
    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.full_name)
            unique_slug = f"{base_slug}-{uuid.uuid4().hex[:8]}"
            self.slug = unique_slug
        super().save(*args, **kwargs)
        
    class Meta:
        verbose_name = "Tamu"
        verbose_name_plural = "Tamu"
        ordering = ['-created_at']


class InvitationCode(models.Model):
    """Generate Kode Unik/QR untuk Tamu"""
    guest = models.OneToOneField(Guest, on_delete=models.CASCADE, verbose_name="Tamu")
    unique_code = models.CharField(max_length=20, unique=True, verbose_name="Kode Unik")
    qr_code_image = models.ImageField(upload_to='invitation_qr/', blank=True, null=True, verbose_name="QR Code")
    invitation_url = models.URLField(max_length=500, blank=True, verbose_name="URL Undangan Personal")
    expiry_date = models.DateTimeField(blank=True, null=True, verbose_name="Tanggal Kadaluarsa")
    is_used = models.BooleanField(default=False, verbose_name="Sudah Digunakan")
    used_at = models.DateTimeField(blank=True, null=True, verbose_name="Digunakan Pada")
    scan_count = models.PositiveIntegerField(default=0, verbose_name="Jumlah Scan")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Dibuat Pada")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Diupdate Pada")
    
    def __str__(self):
        return f"Code: {self.unique_code} - {self.guest.full_name}"
    
    def save(self, *args, **kwargs):
        if not self.unique_code:
            self.unique_code = str(uuid.uuid4()).replace('-', '').upper()[:12]
        super().save(*args, **kwargs)
        
        if not self.qr_code_image:
            self.generate_qr_code()
    
    def generate_qr_code(self):
        """Generate QR Code untuk tamu"""
        qr_data = f"https://invywed.com/invitation/{self.guest.client.user.username}/{self.guest.slug}/?code={self.unique_code}"
        
        qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=10, border=4)
        qr.add_data(qr_data)
        qr.make(fit=True)
        
        qr_image = qr.make_image(fill_color="black", back_color="white")
        buffer = BytesIO()
        qr_image.save(buffer, format='PNG')
        buffer.seek(0)
        
        filename = f'invitation_qr_{self.unique_code}.png'
        self.qr_code_image.save(filename, File(buffer), save=False)
        super().save(update_fields=['qr_code_image'])
        
    class Meta:
        verbose_name = "Kode Undangan"
        verbose_name_plural = "Kode Undangan"


class WhatsAppTemplate(models.Model):
    """Template Pesan WhatsApp untuk Undangan"""
    TEMPLATE_TYPE_CHOICES = [
        ('formal', 'Formal'),
        ('casual', 'Santai'),
        ('family', 'Keluarga'),
        ('friends', 'Teman'),
        ('colleagues', 'Rekan Kerja'),
        ('reminder', 'Pengingat'),
        ('thankyou', 'Terima Kasih'),
    ]
    
    client = models.ForeignKey(ClientProfile, on_delete=models.CASCADE, verbose_name="Klien")
    template_name = models.CharField(max_length=100, verbose_name="Nama Template")
    template_type = models.CharField(max_length=20, choices=TEMPLATE_TYPE_CHOICES, verbose_name="Tipe Template")
    message_content = models.TextField(verbose_name="Isi Pesan")
    variables_info = models.TextField(blank=True, verbose_name="Info Variable ({nama}, {tanggal}, dll)")
    is_default = models.BooleanField(default=False, verbose_name="Template Default")
    usage_count = models.PositiveIntegerField(default=0, verbose_name="Jumlah Penggunaan")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Dibuat Pada")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Diupdate Pada")
    
    def __str__(self):
        return f"{self.template_name} ({self.get_template_type_display()})"
        
    class Meta:
        verbose_name = "Template WhatsApp"
        verbose_name_plural = "Template WhatsApp"


class WhatsAppNumber(models.Model):
    """Nomor WhatsApp untuk Admin (untuk menerima pesan dari user)"""
    phone_number = models.CharField(max_length=20, unique=True, verbose_name="Nomor WhatsApp")
    name = models.CharField(max_length=100, verbose_name="Nama/Nickname")
    description = models.TextField(blank=True, verbose_name="Deskripsi")
    is_active = models.BooleanField(default=True, verbose_name="Status Aktif")
    is_default = models.BooleanField(default=False, verbose_name="Nomor Default")
    api_token = models.CharField(max_length=255, blank=True, verbose_name="API Token (optional)")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Dibuat Pada")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Diupdate Pada")
    
    def __str__(self):
        return f"{self.name} ({self.phone_number})"
    
    def save(self, *args, **kwargs):
        # Ensure only one default number
        if self.is_default:
            WhatsAppNumber.objects.filter(is_default=True).update(is_default=False)
        super().save(*args, **kwargs)
    
    class Meta:
        verbose_name = "Nomor WhatsApp"
        verbose_name_plural = "Nomor WhatsApp"
        ordering = ['-is_default', 'name']


class WhatsAppUserTemplate(models.Model):
    """Template Pesan WhatsApp yang bisa dikirim user ke admin"""
    TEMPLATE_TYPE_CHOICES = [
        ('inquiry', 'Pertanyaan'),
        ('order', 'Pemesanan'),
        ('complaint', 'Keluhan'),
        ('suggestion', 'Saran'),
        ('other', 'Lainnya'),
    ]
    
    template_name = models.CharField(max_length=100, verbose_name="Nama Template")
    template_type = models.CharField(max_length=20, choices=TEMPLATE_TYPE_CHOICES, verbose_name="Tipe Template")
    message_content = models.TextField(verbose_name="Isi Pesan")
    variables_info = models.TextField(blank=True, verbose_name="Info Variable ({nama}, {email}, dll)")
    is_active = models.BooleanField(default=True, verbose_name="Status Aktif")
    is_default = models.BooleanField(default=False, verbose_name="Template Default")
    usage_count = models.PositiveIntegerField(default=0, verbose_name="Jumlah Penggunaan")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Dibuat Pada")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Diupdate Pada")
    
    def __str__(self):
        return f"{self.template_name} ({self.get_template_type_display()})"
    
    def save(self, *args, **kwargs):
        # Ensure only one default template per type
        if self.is_default:
            WhatsAppUserTemplate.objects.filter(
                template_type=self.template_type,
                is_default=True
            ).exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)
    
    class Meta:
        verbose_name = "Template WhatsApp User"
        verbose_name_plural = "Template WhatsApp User"
        ordering = ['template_type', 'template_name']


class WhatsAppLog(models.Model):
    """Log Pengiriman WhatsApp"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('sent', 'Terkirim'),
        ('delivered', 'Delivered'),
        ('read', 'Dibaca'),
        ('failed', 'Gagal'),
        ('blocked', 'Diblokir'),
    ]
    
    guest = models.ForeignKey(Guest, on_delete=models.CASCADE, verbose_name="Tamu")
    template = models.ForeignKey(WhatsAppTemplate, on_delete=models.SET_NULL, null=True, verbose_name="Template")
    phone_number = models.CharField(max_length=20, verbose_name="No HP Tujuan")
    message_content = models.TextField(verbose_name="Isi Pesan")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name="Status")
    error_message = models.TextField(blank=True, verbose_name="Pesan Error")
    sent_at = models.DateTimeField(blank=True, null=True, verbose_name="Dikirim Pada")
    delivered_at = models.DateTimeField(blank=True, null=True, verbose_name="Delivered Pada")
    read_at = models.DateTimeField(blank=True, null=True, verbose_name="Dibaca Pada")
    response_data = models.JSONField(blank=True, null=True, verbose_name="Response API")
    retry_count = models.PositiveIntegerField(default=0, verbose_name="Jumlah Retry")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Dibuat Pada")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Diupdate Pada")
    
    def __str__(self):
        return f"WA Log: {self.guest.full_name} - {self.status}"
        
    class Meta:
        verbose_name = "Log WhatsApp"
        verbose_name_plural = "Log WhatsApp"
        ordering = ['-created_at']


class RSVPResponse(models.Model):
    """Response RSVP dari Tamu"""
    ATTENDANCE_CHOICES = [
        ('attending', 'Hadir'),
        ('maybe', 'Mungkin Hadir'),
        ('not_attending', 'Tidak Hadir'),
        ('pending', 'Belum Konfirmasi'),
    ]
    
    EVENT_CHOICES = [
        ('akad', 'Akad'),
        ('resepsi', 'Resepsi'),
        ('both', 'Keduanya'),
    ]
    
    guest = models.OneToOneField(Guest, on_delete=models.CASCADE, verbose_name="Tamu")
    attendance_status = models.CharField(max_length=20, choices=ATTENDANCE_CHOICES, default='pending', verbose_name="Status Kehadiran")
    attending_event = models.CharField(max_length=20, choices=EVENT_CHOICES, blank=True, verbose_name="Acara yang Dihadiri")
    companion_count = models.PositiveIntegerField(default=1, verbose_name="Jumlah Pendamping")
    dietary_requirements = models.TextField(blank=True, verbose_name="Kebutuhan Diet Khusus")
    special_requests = models.TextField(blank=True, verbose_name="Permintaan Khusus")
    response_date = models.DateTimeField(auto_now_add=True, verbose_name="Tanggal Response")
    ip_address = models.GenericIPAddressField(blank=True, null=True, verbose_name="IP Address")
    user_agent = models.TextField(blank=True, verbose_name="User Agent")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Dibuat Pada")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Diupdate Pada")
    
    def __str__(self):
        return f"RSVP: {self.guest.full_name} - {self.get_attendance_status_display()}"
        
    class Meta:
        verbose_name = "Response RSVP"
        verbose_name_plural = "Response RSVP"


class GuestWishes(models.Model):
    """Ucapan & Doa dari Tamu"""
    WISH_TYPE_CHOICES = [
        ('congratulations', 'Ucapan Selamat'),
        ('prayer', 'Doa'),
        ('advice', 'Nasihat'),
        ('memory', 'Kenangan'),
        ('blessing', 'Berkah'),
    ]
    
    guest = models.ForeignKey(Guest, on_delete=models.CASCADE, verbose_name="Tamu")
    wish_type = models.CharField(max_length=20, choices=WISH_TYPE_CHOICES, default='congratulations', verbose_name="Tipe Ucapan")
    wish_content = models.TextField(verbose_name="Isi Ucapan/Doa")
    is_approved = models.BooleanField(default=True, verbose_name="Disetujui")
    is_featured = models.BooleanField(default=False, verbose_name="Ucapan Unggulan")
    likes_count = models.PositiveIntegerField(default=0, verbose_name="Jumlah Suka")
    ip_address = models.GenericIPAddressField(blank=True, null=True, verbose_name="IP Address")
    submitted_at = models.DateTimeField(auto_now_add=True, verbose_name="Dikirim Pada")
    approved_at = models.DateTimeField(blank=True, null=True, verbose_name="Disetujui Pada")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Dibuat Pada")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Diupdate Pada")
    
    def __str__(self):
        return f"Ucapan dari {self.guest.full_name}"
        
    class Meta:
        verbose_name = "Ucapan Tamu"
        verbose_name_plural = "Ucapan Tamu"
        ordering = ['-submitted_at']


class CheckInLog(models.Model):
    """Log Check-In Tamu di Lokasi"""
    EVENT_CHOICES = [
        ('akad', 'Akad'),
        ('resepsi', 'Resepsi'),
        ('other', 'Acara Lain'),
    ]
    
    guest = models.ForeignKey(Guest, on_delete=models.CASCADE, verbose_name="Tamu")
    event_type = models.CharField(max_length=20, choices=EVENT_CHOICES, verbose_name="Jenis Acara")
    check_in_time = models.DateTimeField(default=timezone.now, verbose_name="Waktu Check-In")
    location = models.CharField(max_length=200, blank=True, verbose_name="Lokasi Check-In")
    companion_actual = models.PositiveIntegerField(verbose_name="Jumlah Pendamping Aktual")
    notes = models.TextField(blank=True, verbose_name="Catatan")
    scanned_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name="Discanned Oleh")
    qr_code_used = models.CharField(max_length=50, blank=True, verbose_name="Kode QR yang Digunakan")
    is_late = models.BooleanField(default=False, verbose_name="Terlambat")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Dibuat Pada")
    
    def __str__(self):
        return f"Check-In: {self.guest.full_name} - {self.check_in_time}"
        
    class Meta:
        verbose_name = "Log Check-In"
        verbose_name_plural = "Log Check-In"
        ordering = ['-check_in_time']


class TableAssignment(models.Model):
    """Pengaturan Nomor Meja Tamu"""
    client = models.ForeignKey(ClientProfile, on_delete=models.CASCADE, verbose_name="Klien")
    table_number = models.CharField(max_length=10, verbose_name="Nomor Meja")
    table_name = models.CharField(max_length=100, blank=True, verbose_name="Nama Meja")
    capacity = models.PositiveIntegerField(verbose_name="Kapasitas Meja")
    location_description = models.TextField(blank=True, verbose_name="Deskripsi Lokasi Meja")
    special_notes = models.TextField(blank=True, verbose_name="Catatan Khusus")
    is_vip_table = models.BooleanField(default=False, verbose_name="Meja VIP")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Dibuat Pada")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Diupdate Pada")
    
    def __str__(self):
        return f"Meja {self.table_number} - {self.client.user.username}"
        
    class Meta:
        verbose_name = "Pengaturan Meja"
        verbose_name_plural = "Pengaturan Meja"
        unique_together = ['client', 'table_number']


class SouvenirLog(models.Model):
    """Log Pengambilan Souvenir oleh Tamu"""
    SOUVENIR_TYPE_CHOICES = [
        ('gift_bag', 'Goodie Bag'),
        ('photo_frame', 'Frame Foto'),
        ('keychain', 'Gantungan Kunci'),
        ('mug', 'Mug'),
        ('notebook', 'Buku Catatan'),
        ('snack_box', 'Snack Box'),
        ('flower', 'Bunga'),
        ('other', 'Lainnya'),
    ]
    
    guest = models.ForeignKey(Guest, on_delete=models.CASCADE, verbose_name="Tamu")
    souvenir_type = models.CharField(max_length=20, choices=SOUVENIR_TYPE_CHOICES, verbose_name="Jenis Souvenir")
    souvenir_description = models.CharField(max_length=200, blank=True, verbose_name="Deskripsi Souvenir")
    quantity = models.PositiveIntegerField(default=1, verbose_name="Jumlah")
    picked_up_at = models.DateTimeField(default=timezone.now, verbose_name="Diambil Pada")
    handed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name="Diserahkan Oleh")
    notes = models.TextField(blank=True, verbose_name="Catatan")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Dibuat Pada")
    
    def __str__(self):
        return f"Souvenir: {self.guest.full_name} - {self.get_souvenir_type_display()}"
        
    class Meta:
        verbose_name = "Log Souvenir"
        verbose_name_plural = "Log Souvenir"
        ordering = ['-picked_up_at']


class GuestTag(models.Model):
    """Tag/Label untuk Tamu"""
    client = models.ForeignKey(ClientProfile, on_delete=models.CASCADE, verbose_name="Klien")
    tag_name = models.CharField(max_length=50, verbose_name="Nama Tag")
    tag_color = models.CharField(max_length=7, default="#6c757d", verbose_name="Warna Tag")
    description = models.TextField(blank=True, verbose_name="Deskripsi")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Dibuat Pada")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Diupdate Pada")
    
    def __str__(self):
        return f"Tag: {self.tag_name}"
        
    class Meta:
        verbose_name = "Tag Tamu"
        verbose_name_plural = "Tag Tamu"
        unique_together = ['client', 'tag_name']


class ScanOperator(models.Model):
    """Akun Petugas yang Boleh Scan QR"""
    client = models.ForeignKey(ClientProfile, on_delete=models.CASCADE, verbose_name="Klien")
    operator = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Petugas")
    operator_name = models.CharField(max_length=100, verbose_name="Nama Petugas")
    phone_number = models.CharField(max_length=20, verbose_name="No HP")
    role = models.CharField(max_length=50, default="Penerima Tamu", verbose_name="Peran")
    assigned_location = models.CharField(max_length=100, blank=True, verbose_name="Lokasi Tugas")
    permissions = models.JSONField(default=dict, verbose_name="Permission")
    is_active = models.BooleanField(default=True, verbose_name="Status Aktif")
    last_scan = models.DateTimeField(blank=True, null=True, verbose_name="Scan Terakhir")
    total_scans = models.PositiveIntegerField(default=0, verbose_name="Total Scan")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Dibuat Pada")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Diupdate Pada")
    
    def __str__(self):
        return f"Petugas: {self.operator_name} - {self.client.user.username}"
        
    class Meta:
        verbose_name = "Petugas Scanner"
        verbose_name_plural = "Petugas Scanner"
        unique_together = ['client', 'operator']


class DigitalEnvelope(models.Model):
    """Pencatatan Amplop Digital/Sumbangan"""
    ENVELOPE_TYPE_CHOICES = [
        ('cash', 'Uang Tunai'),
        ('transfer', 'Transfer Bank'),
        ('ewallet', 'E-Wallet'),
        ('gift', 'Kado/Barang'),
    ]
    
    guest = models.ForeignKey(Guest, on_delete=models.CASCADE, verbose_name="Tamu")
    envelope_type = models.CharField(max_length=20, choices=ENVELOPE_TYPE_CHOICES, verbose_name="Jenis Amplop")
    amount = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True, verbose_name="Nominal")
    gift_description = models.CharField(max_length=200, blank=True, verbose_name="Deskripsi Kado")
    message = models.TextField(blank=True, verbose_name="Pesan")
    received_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name="Diterima Oleh")
    received_at = models.DateTimeField(default=timezone.now, verbose_name="Diterima Pada")
    proof_image = models.ImageField(upload_to='envelope_proofs/', blank=True, null=True, verbose_name="Bukti Transfer/Foto")
    is_verified = models.BooleanField(default=False, verbose_name="Terverifikasi")
    notes = models.TextField(blank=True, verbose_name="Catatan")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Dibuat Pada")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Diupdate Pada")
    
    def __str__(self):
        return f"Amplop: {self.guest.full_name} - {self.amount or self.gift_description}"
        
    class Meta:
        verbose_name = "Amplop Digital"
        verbose_name_plural = "Amplop Digital"
        ordering = ['-received_at']


class BroadcastSchedule(models.Model):
    """Jadwal Broadcast Undangan"""
    BROADCAST_TYPE_CHOICES = [
        ('invitation', 'Undangan Awal'),
        ('reminder_1', 'Pengingat 1 (1 minggu)'),
        ('reminder_2', 'Pengingat 2 (1 hari)'),
        ('thankyou', 'Terima Kasih'),
        ('custom', 'Custom'),
    ]
    
    STATUS_CHOICES = [
        ('scheduled', 'Terjadwal'),
        ('processing', 'Sedang Proses'),
        ('completed', 'Selesai'),
        ('failed', 'Gagal'),
        ('cancelled', 'Dibatalkan'),
    ]
    
    client = models.ForeignKey(ClientProfile, on_delete=models.CASCADE, verbose_name="Klien")
    broadcast_name = models.CharField(max_length=100, verbose_name="Nama Broadcast")
    broadcast_type = models.CharField(max_length=20, choices=BROADCAST_TYPE_CHOICES, verbose_name="Jenis Broadcast")
    template = models.ForeignKey(WhatsAppTemplate, on_delete=models.CASCADE, verbose_name="Template Pesan")
    target_groups = models.ManyToManyField(GuestGroup, blank=True, verbose_name="Target Group")
    scheduled_time = models.DateTimeField(verbose_name="Waktu Terjadwal")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled', verbose_name="Status")
    total_targets = models.PositiveIntegerField(default=0, verbose_name="Total Target")
    sent_count = models.PositiveIntegerField(default=0, verbose_name="Jumlah Terkirim")
    failed_count = models.PositiveIntegerField(default=0, verbose_name="Jumlah Gagal")
    started_at = models.DateTimeField(blank=True, null=True, verbose_name="Mulai Pada")
    completed_at = models.DateTimeField(blank=True, null=True, verbose_name="Selesai Pada")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Dibuat Pada")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Diupdate Pada")
    
    def __str__(self):
        return f"Broadcast: {self.broadcast_name} - {self.scheduled_time}"
        
    class Meta:
        verbose_name = "Jadwal Broadcast"
        verbose_name_plural = "Jadwal Broadcast"
        ordering = ['-scheduled_time']


class GuestFeedback(models.Model):
    """Kritik & Saran Tamu untuk Acara"""
    RATING_CHOICES = [
        (1, '1 - Sangat Kurang'),
        (2, '2 - Kurang'),
        (3, '3 - Cukup'),
        (4, '4 - Baik'),
        (5, '5 - Sangat Baik'),
    ]
    
    CATEGORY_CHOICES = [
        ('overall', 'Keseluruhan'),
        ('venue', 'Tempat/Venue'),
        ('food', 'Makanan'),
        ('service', 'Pelayanan'),
        ('entertainment', 'Hiburan'),
        ('decoration', 'Dekorasi'),
        ('invitation', 'Undangan Digital'),
    ]
    
    guest = models.ForeignKey(Guest, on_delete=models.CASCADE, verbose_name="Tamu")
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='overall', verbose_name="Kategori")
    rating = models.PositiveIntegerField(choices=RATING_CHOICES, verbose_name="Rating")
    feedback_text = models.TextField(verbose_name="Kritik & Saran")
    suggestions = models.TextField(blank=True, verbose_name="Saran Perbaikan")
    would_recommend = models.BooleanField(default=True, verbose_name="Akan Merekomendasikan")
    is_anonymous = models.BooleanField(default=False, verbose_name="Anonim")
    is_approved = models.BooleanField(default=True, verbose_name="Disetujui")
    submitted_at = models.DateTimeField(auto_now_add=True, verbose_name="Dikirim Pada")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Dibuat Pada")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Diupdate Pada")
    
    def __str__(self):
        return f"Feedback: {self.guest.full_name} - Rating {self.rating}"
        
    class Meta:
        verbose_name = "Feedback Tamu"
        verbose_name_plural = "Feedback Tamu"
        ordering = ['-submitted_at']
