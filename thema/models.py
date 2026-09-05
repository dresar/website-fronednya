from django.db import models
from django.utils.text import slugify
from django.core.validators import FileExtensionValidator
import os
import uuid


class ThemeCategory(models.Model):
    """Kategori untuk tema"""
    name = models.CharField(max_length=100, verbose_name="Nama Kategori")
    slug = models.SlugField(max_length=120, unique=True, verbose_name="Slug")
    description = models.TextField(blank=True, verbose_name="Deskripsi")
    icon_class = models.CharField(max_length=50, blank=True, verbose_name="CSS Icon Class")
    order = models.PositiveIntegerField(default=0, verbose_name="Urutan")
    is_active = models.BooleanField(default=True, verbose_name="Status Aktif")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Dibuat Pada")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Diupdate Pada")
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = "Kategori Tema"
        verbose_name_plural = "Kategori Tema"
        ordering = ['order', 'name']


class Theme(models.Model):
    """Model untuk Template Tema Undangan"""
    DIFFICULTY_CHOICES = [
        ('beginner', 'Beginner'),
        ('intermediate', 'Intermediate'),
        ('advanced', 'Advanced'),
    ]
    
    name = models.CharField(max_length=200, verbose_name="Nama Tema")
    slug = models.SlugField(max_length=250, unique=True, verbose_name="Slug", blank=True)
    description = models.TextField(blank=True, verbose_name="Deskripsi")
    category = models.ForeignKey(ThemeCategory, on_delete=models.SET_NULL, null=True, blank=True, 
                                 related_name='themes', verbose_name="Kategori")
    
    # File uploads
    zip_file = models.FileField(
        upload_to='themes/zip/',
        verbose_name="File ZIP Template",
        help_text="Upload file ZIP yang berisi HTML, CSS, JS template",
        validators=[FileExtensionValidator(allowed_extensions=['zip'])]
    )
    thumbnail = models.ImageField(
        upload_to='themes/thumbnails/',
        blank=True,
        null=True,
        verbose_name="Thumbnail",
        help_text="Gambar preview tema"
    )
    
    # Metadata
    difficulty_level = models.CharField(
        max_length=20,
        choices=DIFFICULTY_CHOICES,
        default='beginner',
        verbose_name="Tingkat Kesulitan"
    )
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        verbose_name="Harga"
    )
    is_premium = models.BooleanField(default=False, verbose_name="Premium")
    is_active = models.BooleanField(default=True, verbose_name="Status Aktif")
    
    # Stats
    download_count = models.PositiveIntegerField(default=0, verbose_name="Jumlah Download")
    view_count = models.PositiveIntegerField(default=0, verbose_name="Jumlah Dilihat")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Dibuat Pada")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Diupdate Pada")
    
    # Path untuk extracted files
    extracted_path = models.CharField(
        max_length=500,
        blank=True,
        verbose_name="Path Template",
        help_text="Path ke folder template yang sudah diextract"
    )
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        # Generate slug jika belum ada
        if not self.slug:
            self.slug = slugify(self.name)
            # Handle duplicate slug
            base_slug = self.slug
            counter = 1
            while Theme.objects.filter(slug=self.slug).exclude(pk=self.pk).exists():
                self.slug = f"{base_slug}-{counter}"
                counter += 1
        
        super().save(*args, **kwargs)
    
    def get_template_path(self):
        """Mendapatkan path lengkap ke folder template"""
        if self.extracted_path:
            return self.extracted_path
        return None
    
    def get_demo_url(self):
        """Mendapatkan URL untuk demo tema"""
        return f"/demo/{self.slug}/"
    
    class Meta:
        verbose_name = "Tema"
        verbose_name_plural = "Tema"
        ordering = ['-created_at']
