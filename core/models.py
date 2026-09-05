from django.db import models
from django.contrib.auth.models import User
from django_summernote.fields import SummernoteTextField
from django.utils.text import slugify
from users.models import ClientProfile
import uuid
from django.utils import timezone

# Create your models here.

class PricingPackage(models.Model):
    """Paket Harga Layanan"""
    PACKAGE_TYPE_CHOICES = [
        ('free', 'Free'),
        ('basic', 'Basic'),
        ('premium', 'Premium'),
        ('gold', 'Gold'),
        ('platinum', 'Platinum'),
        ('enterprise', 'Enterprise'),
    ]
    
    BILLING_PERIOD_CHOICES = [
        ('monthly', 'Bulanan'),
        ('quarterly', 'Per 3 Bulan'),
        ('semi_annual', 'Per 6 Bulan'),
        ('annual', 'Tahunan'),
        ('lifetime', 'Seumur Hidup'),
        ('per_event', 'Per Acara'),
    ]
    
    package_name = models.CharField(max_length=100, verbose_name="Nama Paket")
    package_type = models.CharField(max_length=20, choices=PACKAGE_TYPE_CHOICES, verbose_name="Tipe Paket")
    slug = models.SlugField(max_length=120, unique=True, verbose_name="Slug")
    description = SummernoteTextField(blank=True, verbose_name="Deskripsi Paket")
    short_description = models.CharField(max_length=200, blank=True, verbose_name="Deskripsi Singkat")
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Harga")
    original_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, verbose_name="Harga Normal")
    billing_period = models.CharField(max_length=20, choices=BILLING_PERIOD_CHOICES, default='monthly', verbose_name="Periode Tagihan")
    max_invitations = models.PositiveIntegerField(default=1, verbose_name="Maksimal Undangan")
    max_guests = models.PositiveIntegerField(default=100, verbose_name="Maksimal Tamu")
    max_templates = models.PositiveIntegerField(default=5, verbose_name="Maksimal Template")
    storage_limit_gb = models.DecimalField(max_digits=5, decimal_places=2, default=1.0, verbose_name="Batas Penyimpanan (GB)")
    is_popular = models.BooleanField(default=False, verbose_name="Paket Populer")
    is_active = models.BooleanField(default=True, verbose_name="Status Aktif")
    order = models.PositiveIntegerField(default=0, verbose_name="Urutan")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Dibuat Pada")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Diupdate Pada")
    
    def __str__(self):
        return f"{self.package_name} - Rp {self.price:,.2f}"
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.package_name)
        super().save(*args, **kwargs)
        
    class Meta:
        verbose_name = "Paket Harga"
        verbose_name_plural = "Paket Harga"
        ordering = ['order', 'price']


class PackageFeature(models.Model):
    """Fitur Detail per Paket"""
    FEATURE_TYPE_CHOICES = [
        ('included', 'Termasuk'),
        ('limited', 'Terbatas'),
        ('unlimited', 'Unlimited'),
        ('not_included', 'Tidak Termasuk'),
        ('addon', 'Add-on'),
    ]
    
    package = models.ForeignKey(PricingPackage, related_name='features', on_delete=models.CASCADE, verbose_name="Paket")
    feature_name = models.CharField(max_length=200, verbose_name="Nama Fitur")
    feature_description = models.TextField(blank=True, verbose_name="Deskripsi Fitur")
    feature_type = models.CharField(max_length=20, choices=FEATURE_TYPE_CHOICES, verbose_name="Tipe Fitur")
    feature_limit = models.CharField(max_length=100, blank=True, verbose_name="Batas/Limit")
    icon_class = models.CharField(max_length=50, blank=True, verbose_name="CSS Icon Class")
    is_highlighted = models.BooleanField(default=False, verbose_name="Fitur Unggulan")
    order = models.PositiveIntegerField(default=0, verbose_name="Urutan")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Dibuat Pada")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Diupdate Pada")
    
    def __str__(self):
        return f"{self.feature_name} - {self.package.package_name}"
        
    class Meta:
        verbose_name = "Fitur Paket"
        verbose_name_plural = "Fitur Paket"
        ordering = ['package', 'order']


class DiscountCoupon(models.Model):
    """Kode Promo/Diskon"""
    DISCOUNT_TYPE_CHOICES = [
        ('percentage', 'Persentase'),
        ('fixed_amount', 'Nominal Tetap'),
        ('free_shipping', 'Gratis Ongkir'),
        ('bogo', 'Buy One Get One'),
    ]
    
    COUPON_STATUS_CHOICES = [
        ('active', 'Aktif'),
        ('expired', 'Kadaluarsa'),
        ('used_up', 'Habis Digunakan'),
        ('disabled', 'Dinonaktifkan'),
    ]
    
    coupon_code = models.CharField(max_length=50, unique=True, verbose_name="Kode Kupon")
    coupon_name = models.CharField(max_length=100, verbose_name="Nama Kupon")
    description = models.TextField(blank=True, verbose_name="Deskripsi")
    discount_type = models.CharField(max_length=20, choices=DISCOUNT_TYPE_CHOICES, verbose_name="Tipe Diskon")
    discount_value = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Nilai Diskon")
    minimum_purchase = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Minimal Pembelian")
    maximum_discount = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, verbose_name="Maksimal Diskon")
    usage_limit = models.PositiveIntegerField(blank=True, null=True, verbose_name="Batas Penggunaan")
    usage_count = models.PositiveIntegerField(default=0, verbose_name="Jumlah Penggunaan")
    per_user_limit = models.PositiveIntegerField(default=1, verbose_name="Batas per User")
    valid_from = models.DateTimeField(verbose_name="Berlaku Dari")
    valid_until = models.DateTimeField(verbose_name="Berlaku Sampai")
    status = models.CharField(max_length=20, choices=COUPON_STATUS_CHOICES, default='active', verbose_name="Status")
    applicable_packages = models.ManyToManyField(PricingPackage, blank=True, verbose_name="Paket yang Berlaku")
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name="Dibuat Oleh")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Dibuat Pada")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Diupdate Pada")
    
    def __str__(self):
        return f"{self.coupon_code} - {self.coupon_name}"
        
    class Meta:
        verbose_name = "Kupon Diskon"
        verbose_name_plural = "Kupon Diskon"
        ordering = ['-created_at']


class Transaction(models.Model):
    """Data Transaksi/Pembayaran User"""
    TRANSACTION_STATUS_CHOICES = [
        ('pending', 'Menunggu Pembayaran'),
        ('processing', 'Sedang Diproses'),
        ('paid', 'Sudah Dibayar'),
        ('confirmed', 'Dikonfirmasi'),
        ('expired', 'Kadaluarsa'),
        ('cancelled', 'Dibatalkan'),
        ('refunded', 'Dikembalikan'),
        ('failed', 'Gagal'),
    ]
    
    PAYMENT_METHOD_CHOICES = [
        ('bank_transfer', 'Transfer Bank'),
        ('virtual_account', 'Virtual Account'),
        ('credit_card', 'Kartu Kredit'),
        ('debit_card', 'Kartu Debit'),
        ('ewallet', 'E-Wallet'),
        ('qris', 'QRIS'),
        ('cod', 'Cash on Delivery'),
    ]
    
    transaction_id = models.CharField(max_length=100, unique=True, verbose_name="ID Transaksi")
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="User")
    package = models.ForeignKey(PricingPackage, on_delete=models.CASCADE, verbose_name="Paket")
    coupon = models.ForeignKey(DiscountCoupon, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Kupon")
    gross_amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Jumlah Kotor")
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="Jumlah Diskon")
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="Pajak")
    net_amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Jumlah Bersih")
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, verbose_name="Metode Pembayaran")
    status = models.CharField(max_length=20, choices=TRANSACTION_STATUS_CHOICES, default='pending', verbose_name="Status")
    payment_proof = models.ImageField(upload_to='payment_proofs/', blank=True, null=True, verbose_name="Bukti Pembayaran")
    payment_date = models.DateTimeField(blank=True, null=True, verbose_name="Tanggal Pembayaran")
    confirmed_date = models.DateTimeField(blank=True, null=True, verbose_name="Tanggal Konfirmasi")
    expires_at = models.DateTimeField(verbose_name="Kadaluarsa Pada")
    billing_period_start = models.DateTimeField(verbose_name="Periode Mulai")
    billing_period_end = models.DateTimeField(verbose_name="Periode Berakhir")
    notes = models.TextField(blank=True, verbose_name="Catatan")
    gateway_response = models.JSONField(blank=True, null=True, verbose_name="Response Payment Gateway")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Dibuat Pada")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Diupdate Pada")
    
    def __str__(self):
        return f"{self.transaction_id} - {self.user.username} - Rp {self.net_amount:,.2f}"
    
    def save(self, *args, **kwargs):
        if not self.transaction_id:
            self.transaction_id = f"INV-{timezone.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)
        
    class Meta:
        verbose_name = "Transaksi"
        verbose_name_plural = "Transaksi"
        ordering = ['-created_at']


class PaymentMethod(models.Model):
    """Metode Pembayaran yang Tersedia"""
    METHOD_TYPE_CHOICES = [
        ('bank', 'Bank'),
        ('ewallet', 'E-Wallet'),
        ('virtual_account', 'Virtual Account'),
        ('qris', 'QRIS'),
        ('credit_card', 'Kartu Kredit'),
    ]
    
    method_name = models.CharField(max_length=100, verbose_name="Nama Metode")
    method_type = models.CharField(max_length=20, choices=METHOD_TYPE_CHOICES, verbose_name="Tipe Metode")
    bank_name = models.CharField(max_length=100, blank=True, verbose_name="Nama Bank")
    account_number = models.CharField(max_length=50, blank=True, verbose_name="Nomor Rekening")
    account_name = models.CharField(max_length=200, blank=True, verbose_name="Nama Pemilik")
    logo_image = models.ImageField(upload_to='payment_logos/', blank=True, null=True, verbose_name="Logo")
    instructions = SummernoteTextField(blank=True, verbose_name="Instruksi Pembayaran")
    admin_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Biaya Admin")
    is_active = models.BooleanField(default=True, verbose_name="Status Aktif")
    order = models.PositiveIntegerField(default=0, verbose_name="Urutan")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Dibuat Pada")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Diupdate Pada")
    
    def __str__(self):
        return f"{self.method_name} ({self.get_method_type_display()})"
        
    class Meta:
        verbose_name = "Metode Pembayaran"
        verbose_name_plural = "Metode Pembayaran"
        ordering = ['order', 'method_name']


class RefundRequest(models.Model):
    """Permintaan Pengembalian Dana"""
    REFUND_STATUS_CHOICES = [
        ('pending', 'Menunggu Review'),
        ('approved', 'Disetujui'),
        ('processing', 'Sedang Diproses'),
        ('completed', 'Selesai'),
        ('rejected', 'Ditolak'),
    ]
    
    REFUND_REASON_CHOICES = [
        ('technical_issue', 'Masalah Teknis'),
        ('service_issue', 'Masalah Layanan'),
        ('change_of_mind', 'Berubah Pikiran'),
        ('duplicate_payment', 'Pembayaran Ganda'),
        ('cancelled_event', 'Acara Dibatalkan'),
        ('other', 'Lainnya'),
    ]
    
    transaction = models.OneToOneField(Transaction, on_delete=models.CASCADE, verbose_name="Transaksi")
    refund_amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Jumlah Refund")
    refund_reason = models.CharField(max_length=30, choices=REFUND_REASON_CHOICES, verbose_name="Alasan Refund")
    reason_description = models.TextField(verbose_name="Deskripsi Alasan")
    status = models.CharField(max_length=20, choices=REFUND_STATUS_CHOICES, default='pending', verbose_name="Status")
    requested_by = models.ForeignKey(User, related_name='refund_requests', on_delete=models.CASCADE, verbose_name="Diminta Oleh")
    approved_by = models.ForeignKey(User, related_name='approved_refunds', on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Disetujui Oleh")
    bank_account_name = models.CharField(max_length=200, blank=True, verbose_name="Nama Pemilik Rekening")
    bank_account_number = models.CharField(max_length=50, blank=True, verbose_name="Nomor Rekening")
    bank_name = models.CharField(max_length=100, blank=True, verbose_name="Nama Bank")
    refund_proof = models.ImageField(upload_to='refund_proofs/', blank=True, null=True, verbose_name="Bukti Refund")
    admin_notes = models.TextField(blank=True, verbose_name="Catatan Admin")
    requested_at = models.DateTimeField(auto_now_add=True, verbose_name="Diminta Pada")
    processed_at = models.DateTimeField(blank=True, null=True, verbose_name="Diproses Pada")
    completed_at = models.DateTimeField(blank=True, null=True, verbose_name="Selesai Pada")
    
    def __str__(self):
        return f"Refund {self.transaction.transaction_id} - Rp {self.refund_amount:,.2f}"
        
    class Meta:
        verbose_name = "Permintaan Refund"
        verbose_name_plural = "Permintaan Refund"
        ordering = ['-requested_at']


class SupportTicket(models.Model):
    """Tiket Bantuan/Support"""
    PRIORITY_CHOICES = [
        ('low', 'Rendah'),
        ('normal', 'Normal'),
        ('high', 'Tinggi'),
        ('urgent', 'Mendesak'),
        ('critical', 'Kritis'),
    ]
    
    STATUS_CHOICES = [
        ('open', 'Terbuka'),
        ('in_progress', 'Dalam Proses'),
        ('waiting_customer', 'Menunggu Customer'),
        ('resolved', 'Terselesaikan'),
        ('closed', 'Ditutup'),
        ('cancelled', 'Dibatalkan'),
    ]
    
    CATEGORY_CHOICES = [
        ('technical', 'Masalah Teknis'),
        ('billing', 'Masalah Tagihan'),
        ('feature_request', 'Permintaan Fitur'),
        ('bug_report', 'Laporan Bug'),
        ('account', 'Masalah Akun'),
        ('template', 'Masalah Template'),
        ('guest_management', 'Manajemen Tamu'),
        ('general', 'Umum'),
    ]
    
    ticket_id = models.CharField(max_length=20, unique=True, verbose_name="ID Tiket")
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="User")
    subject = models.CharField(max_length=200, verbose_name="Subjek")
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, verbose_name="Kategori")
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='normal', verbose_name="Prioritas")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open', verbose_name="Status")
    description = models.TextField(verbose_name="Deskripsi Masalah")
    assigned_to = models.ForeignKey(User, related_name='assigned_tickets', on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Ditangani Oleh")
    attachment = models.FileField(upload_to='ticket_attachments/', blank=True, null=True, verbose_name="Lampiran")
    resolution = models.TextField(blank=True, verbose_name="Solusi")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Dibuat Pada")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Diupdate Pada")
    resolved_at = models.DateTimeField(blank=True, null=True, verbose_name="Terselesaikan Pada")
    closed_at = models.DateTimeField(blank=True, null=True, verbose_name="Ditutup Pada")
    
    def __str__(self):
        return f"Ticket #{self.ticket_id} - {self.subject}"
    
    def save(self, *args, **kwargs):
        if not self.ticket_id:
            self.ticket_id = f"TK-{timezone.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
        super().save(*args, **kwargs)
        
    class Meta:
        verbose_name = "Tiket Support"
        verbose_name_plural = "Tiket Support"
        ordering = ['-created_at']


class TicketReply(models.Model):
    """Balasan/Reply pada Tiket"""
    REPLY_TYPE_CHOICES = [
        ('customer', 'Customer'),
        ('staff', 'Staff'),
        ('system', 'System'),
    ]
    
    ticket = models.ForeignKey(SupportTicket, related_name='replies', on_delete=models.CASCADE, verbose_name="Tiket")
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="User")
    reply_type = models.CharField(max_length=10, choices=REPLY_TYPE_CHOICES, verbose_name="Tipe Balasan")
    message = models.TextField(verbose_name="Pesan")
    attachment = models.FileField(upload_to='ticket_replies/', blank=True, null=True, verbose_name="Lampiran")
    is_internal_note = models.BooleanField(default=False, verbose_name="Catatan Internal")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Dibuat Pada")
    
    def __str__(self):
        return f"Reply to {self.ticket.ticket_id} by {self.user.username}"
        
    class Meta:
        verbose_name = "Balasan Tiket"
        verbose_name_plural = "Balasan Tiket"
        ordering = ['created_at']


class FaqItem(models.Model):
    """FAQ/Pertanyaan yang Sering Diajukan"""
    FAQ_CATEGORY_CHOICES = [
        ('general', 'Umum'),
        ('pricing', 'Harga & Paket'),
        ('features', 'Fitur'),
        ('technical', 'Teknis'),
        ('account', 'Akun'),
        ('payment', 'Pembayaran'),
        ('templates', 'Template'),
        ('guests', 'Manajemen Tamu'),
    ]
    
    question = models.CharField(max_length=300, verbose_name="Pertanyaan")
    answer = SummernoteTextField(verbose_name="Jawaban")
    category = models.CharField(max_length=20, choices=FAQ_CATEGORY_CHOICES, verbose_name="Kategori")
    order = models.PositiveIntegerField(default=0, verbose_name="Urutan")
    is_featured = models.BooleanField(default=False, verbose_name="FAQ Unggulan")
    view_count = models.PositiveIntegerField(default=0, verbose_name="Jumlah Dilihat")
    helpful_count = models.PositiveIntegerField(default=0, verbose_name="Jumlah Membantu")
    not_helpful_count = models.PositiveIntegerField(default=0, verbose_name="Jumlah Tidak Membantu")
    is_active = models.BooleanField(default=True, verbose_name="Status Aktif")
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name="Dibuat Oleh")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Dibuat Pada")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Diupdate Pada")
    
    def __str__(self):
        return f"FAQ: {self.question[:100]}"
        
    class Meta:
        verbose_name = "FAQ"
        verbose_name_plural = "FAQ"
        ordering = ['category', 'order']


class BlogCategory(models.Model):
    """Kategori Blog/Artikel"""
    name = models.CharField(max_length=100, verbose_name="Nama Kategori")
    slug = models.SlugField(max_length=120, unique=True, verbose_name="Slug")
    description = models.TextField(blank=True, verbose_name="Deskripsi")
    color_code = models.CharField(max_length=7, default="#007bff", verbose_name="Kode Warna")
    icon_class = models.CharField(max_length=50, blank=True, verbose_name="CSS Icon Class")
    seo_title = models.CharField(max_length=200, blank=True, verbose_name="SEO Title")
    seo_description = models.CharField(max_length=300, blank=True, verbose_name="SEO Description")
    order = models.PositiveIntegerField(default=0, verbose_name="Urutan")
    is_active = models.BooleanField(default=True, verbose_name="Status Aktif")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Dibuat Pada")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Diupdate Pada")
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
        
    class Meta:
        verbose_name = "Kategori Blog"
        verbose_name_plural = "Kategori Blog"
        ordering = ['order', 'name']


class BlogPost(models.Model):
    """Artikel/Post Blog untuk SEO"""
    POST_STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('published', 'Published'),
        ('scheduled', 'Scheduled'),
        ('archived', 'Archived'),
    ]
    
    title = models.CharField(max_length=200, verbose_name="Judul")
    slug = models.SlugField(max_length=250, unique=True, verbose_name="Slug")
    category = models.ForeignKey(BlogCategory, on_delete=models.CASCADE, verbose_name="Kategori")
    excerpt = models.TextField(blank=True, verbose_name="Ringkasan")
    content = SummernoteTextField(verbose_name="Konten")
    featured_image = models.ImageField(upload_to='blog_images/', blank=True, null=True, verbose_name="Gambar Utama")
    author = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Penulis")
    status = models.CharField(max_length=20, choices=POST_STATUS_CHOICES, default='draft', verbose_name="Status")
    is_featured = models.BooleanField(default=False, verbose_name="Artikel Unggulan")
    view_count = models.PositiveIntegerField(default=0, verbose_name="Jumlah View")
    reading_time = models.PositiveIntegerField(blank=True, null=True, verbose_name="Waktu Baca (menit)")
    tags = models.CharField(max_length=300, blank=True, verbose_name="Tags (comma separated)")
    seo_title = models.CharField(max_length=200, blank=True, verbose_name="SEO Title")
    seo_description = models.CharField(max_length=300, blank=True, verbose_name="SEO Description")
    seo_keywords = models.CharField(max_length=200, blank=True, verbose_name="SEO Keywords")
    published_at = models.DateTimeField(blank=True, null=True, verbose_name="Dipublish Pada")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Dibuat Pada")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Diupdate Pada")
    
    def __str__(self):
        return self.title
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)
        
    class Meta:
        verbose_name = "Post Blog"
        verbose_name_plural = "Post Blog"
        ordering = ['-published_at', '-created_at']


class Testimonial(models.Model):
    """Testimoni/Ulasan dari User"""
    RATING_CHOICES = [
        (1, '1 - Sangat Kurang'),
        (2, '2 - Kurang'),
        (3, '3 - Cukup'),
        (4, '4 - Baik'),
        (5, '5 - Sangat Baik'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="User")
    client_name = models.CharField(max_length=100, verbose_name="Nama Klien")
    client_title = models.CharField(max_length=100, blank=True, verbose_name="Jabatan/Title")
    testimonial_text = models.TextField(verbose_name="Teks Testimoni")
    rating = models.PositiveIntegerField(choices=RATING_CHOICES, verbose_name="Rating")
    client_photo = models.ImageField(upload_to='testimonial_photos/', blank=True, null=True, verbose_name="Foto Klien")
    wedding_photo = models.ImageField(upload_to='testimonial_weddings/', blank=True, null=True, verbose_name="Foto Pernikahan")
    event_date = models.DateField(blank=True, null=True, verbose_name="Tanggal Acara")
    location = models.CharField(max_length=200, blank=True, verbose_name="Lokasi Acara")
    is_featured = models.BooleanField(default=False, verbose_name="Testimoni Unggulan")
    is_approved = models.BooleanField(default=False, verbose_name="Disetujui")
    display_order = models.PositiveIntegerField(default=0, verbose_name="Urutan Tampilan")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Dibuat Pada")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Diupdate Pada")
    
    def __str__(self):
        return f"Testimoni {self.client_name} - Rating {self.rating}"
        
    class Meta:
        verbose_name = "Testimoni"
        verbose_name_plural = "Testimoni"
        ordering = ['display_order', '-created_at']


class PartnerVendor(models.Model):
    """Vendor Partner untuk Rekomendasi"""
    VENDOR_TYPE_CHOICES = [
        ('photographer', 'Fotografer'),
        ('videographer', 'Videografer'),
        ('makeup_artist', 'MUA'),
        ('decoration', 'Dekorasi'),
        ('catering', 'Catering'),
        ('venue', 'Venue'),
        ('entertainment', 'Hiburan'),
        ('wedding_planner', 'Wedding Planner'),
        ('florist', 'Florist'),
        ('transportation', 'Transportasi'),
    ]
    
    vendor_name = models.CharField(max_length=200, verbose_name="Nama Vendor")
    vendor_type = models.CharField(max_length=20, choices=VENDOR_TYPE_CHOICES, verbose_name="Tipe Vendor")
    description = SummernoteTextField(blank=True, verbose_name="Deskripsi")
    contact_person = models.CharField(max_length=100, verbose_name="Contact Person")
    phone_number = models.CharField(max_length=20, verbose_name="No HP")
    email = models.EmailField(blank=True, verbose_name="Email")
    website_url = models.URLField(blank=True, verbose_name="Website")
    instagram_url = models.URLField(blank=True, verbose_name="Instagram")
    address = models.TextField(verbose_name="Alamat")
    city = models.CharField(max_length=100, verbose_name="Kota")
    coverage_area = models.CharField(max_length=200, blank=True, verbose_name="Area Layanan")
    price_range = models.CharField(max_length=100, blank=True, verbose_name="Range Harga")
    logo = models.ImageField(upload_to='vendor_logos/', blank=True, null=True, verbose_name="Logo")
    portfolio_images = models.JSONField(blank=True, null=True, verbose_name="Portfolio Images")
    is_featured = models.BooleanField(default=False, verbose_name="Vendor Unggulan")
    is_verified = models.BooleanField(default=False, verbose_name="Terverifikasi")
    is_active = models.BooleanField(default=True, verbose_name="Status Aktif")
    rating_average = models.DecimalField(max_digits=3, decimal_places=2, default=0.00, verbose_name="Rating Rata-rata")
    review_count = models.PositiveIntegerField(default=0, verbose_name="Jumlah Review")
    order = models.PositiveIntegerField(default=0, verbose_name="Urutan")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Dibuat Pada")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Diupdate Pada")
    
    def __str__(self):
        return f"{self.vendor_name} ({self.get_vendor_type_display()})"
        
    class Meta:
        verbose_name = "Partner Vendor"
        verbose_name_plural = "Partner Vendor"
        ordering = ['vendor_type', 'order', 'vendor_name']


class SiteConfiguration(models.Model):
    """Konfigurasi Website Global"""
    site_name = models.CharField(max_length=100, default="Invywed", verbose_name="Nama Website")
    site_tagline = models.CharField(max_length=200, blank=True, verbose_name="Tagline")
    site_description = models.TextField(blank=True, verbose_name="Deskripsi Website")
    site_logo = models.ImageField(upload_to='site_config/', blank=True, null=True, verbose_name="Logo Website")
    site_favicon = models.ImageField(upload_to='site_config/', blank=True, null=True, verbose_name="Favicon")
    contact_email = models.EmailField(verbose_name="Email Kontak")
    contact_phone = models.CharField(max_length=20, verbose_name="No HP Kontak")
    contact_whatsapp = models.CharField(max_length=20, verbose_name="No WhatsApp")
    contact_address = models.TextField(verbose_name="Alamat")
    social_facebook = models.URLField(blank=True, verbose_name="Facebook")
    social_instagram = models.URLField(blank=True, verbose_name="Instagram")
    social_twitter = models.URLField(blank=True, verbose_name="Twitter")
    social_youtube = models.URLField(blank=True, verbose_name="YouTube")
    social_tiktok = models.URLField(blank=True, verbose_name="TikTok")
    google_analytics_id = models.CharField(max_length=50, blank=True, verbose_name="Google Analytics ID")
    google_tag_manager_id = models.CharField(max_length=50, blank=True, verbose_name="Google Tag Manager ID")
    facebook_pixel_id = models.CharField(max_length=50, blank=True, verbose_name="Facebook Pixel ID")
    maintenance_mode = models.BooleanField(default=False, verbose_name="Mode Maintenance")
    maintenance_message = models.TextField(blank=True, verbose_name="Pesan Maintenance")
    seo_title = models.CharField(max_length=200, blank=True, verbose_name="SEO Title")
    seo_description = models.CharField(max_length=300, blank=True, verbose_name="SEO Description")
    seo_keywords = models.CharField(max_length=200, blank=True, verbose_name="SEO Keywords")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Dibuat Pada")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Diupdate Pada")
    
    def __str__(self):
        return self.site_name
        
    class Meta:
        verbose_name = "Konfigurasi Website"
        verbose_name_plural = "Konfigurasi Website"


class MaintenanceLog(models.Model):
    """Catatan Update/Maintenance Sistem"""
    LOG_TYPE_CHOICES = [
        ('system_update', 'System Update'),
        ('feature_release', 'Feature Release'),
        ('bug_fix', 'Bug Fix'),
        ('security_patch', 'Security Patch'),
        ('maintenance', 'Maintenance'),
        ('downtime', 'Downtime'),
    ]
    
    SEVERITY_CHOICES = [
        ('low', 'Rendah'),
        ('medium', 'Sedang'),
        ('high', 'Tinggi'),
        ('critical', 'Kritis'),
    ]
    
    title = models.CharField(max_length=200, verbose_name="Judul")
    log_type = models.CharField(max_length=20, choices=LOG_TYPE_CHOICES, verbose_name="Tipe Log")
    description = SummernoteTextField(verbose_name="Deskripsi")
    severity = models.CharField(max_length=10, choices=SEVERITY_CHOICES, default='medium', verbose_name="Tingkat Kepentingan")
    version = models.CharField(max_length=20, blank=True, verbose_name="Versi")
    affects_users = models.BooleanField(default=False, verbose_name="Mempengaruhi User")
    downtime_duration = models.CharField(max_length=50, blank=True, verbose_name="Durasi Downtime")
    started_at = models.DateTimeField(verbose_name="Dimulai Pada")
    completed_at = models.DateTimeField(blank=True, null=True, verbose_name="Selesai Pada")
    performed_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Dilakukan Oleh")
    notes = models.TextField(blank=True, verbose_name="Catatan")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Dibuat Pada")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Diupdate Pada")
    
    def __str__(self):
        return f"{self.get_log_type_display()}: {self.title}"
        
    class Meta:
        verbose_name = "Log Maintenance"
        verbose_name_plural = "Log Maintenance"
        ordering = ['-started_at']
