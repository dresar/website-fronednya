from django.db import models
from django_summernote.fields import SummernoteTextField
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
import uuid
import json

# Create your models here.

class Category(models.Model):
    """Kategori Template Undangan"""
    name = models.CharField(max_length=100, verbose_name="Nama Kategori")
    slug = models.SlugField(max_length=120, unique=True, verbose_name="Slug")
    description = SummernoteTextField(blank=True, verbose_name="Deskripsi Kategori")
    icon_class = models.CharField(max_length=50, blank=True, verbose_name="CSS Icon Class")
    cover_image = models.ImageField(upload_to='category_covers/', blank=True, null=True, verbose_name="Gambar Cover")
    order = models.PositiveIntegerField(default=0, verbose_name="Urutan")
    is_featured = models.BooleanField(default=False, verbose_name="Kategori Unggulan")
    is_active = models.BooleanField(default=True, verbose_name="Status Aktif")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Dibuat Pada")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Diupdate Pada")
    
    def __str__(self):
        return self.name
        
    class Meta:
        verbose_name = "Kategori"
        verbose_name_plural = "Kategori"
        ordering = ['order', 'name']




# ===== REMOVED MODELS (Not needed for small website) =====
# ThemeColorPalette, FontPairing, MusicLibrary, BackgroundAsset, DividerAsset,
# OpeningAnimation, ThemeSection, QuoteLibrary, IconSet, TemplateFeature,
# ThemeRating, ThemePreview, CustomCSS
