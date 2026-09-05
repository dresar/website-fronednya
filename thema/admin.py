from django.contrib import admin
from .models import Theme, ThemeCategory


@admin.register(ThemeCategory)
class ThemeCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'order', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'slug', 'description']
    prepopulated_fields = {'slug': ('name',)}
    ordering = ['order', 'name']


@admin.register(Theme)
class ThemeAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'category', 'difficulty_level', 'is_premium', 'is_active', 'download_count', 'view_count', 'created_at']
    list_filter = ['category', 'difficulty_level', 'is_premium', 'is_active', 'created_at']
    search_fields = ['name', 'slug', 'description']
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ['download_count', 'view_count', 'extracted_path', 'created_at', 'updated_at']
    ordering = ['-created_at']
    
    fieldsets = (
        ('Informasi Dasar', {
            'fields': ('name', 'slug', 'description', 'category')
        }),
        ('File', {
            'fields': ('zip_file', 'thumbnail', 'extracted_path')
        }),
        ('Metadata', {
            'fields': ('difficulty_level', 'price', 'is_premium', 'is_active')
        }),
        ('Statistik', {
            'fields': ('download_count', 'view_count')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )
