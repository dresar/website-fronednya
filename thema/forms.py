from django import forms
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
import zipfile
import os

from .models import Theme, ThemeCategory


class ThemeCategoryForm(forms.ModelForm):
    """Form untuk Theme Category - Hanya Nama"""
    
    class Meta:
        model = ThemeCategory
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500',
                'placeholder': 'Masukkan nama kategori',
            }),
        }
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # Auto-generate slug dari nama
        if not instance.slug:
            from django.utils.text import slugify
            instance.slug = slugify(instance.name)
            # Handle duplicate slug
            base_slug = instance.slug
            counter = 1
            while ThemeCategory.objects.filter(slug=instance.slug).exclude(pk=instance.pk).exists():
                instance.slug = f"{base_slug}-{counter}"
                counter += 1
        
        # Set default values
        if not instance.pk:  # New category
            instance.description = ''
            instance.icon_class = ''
            instance.order = 0
            instance.is_active = True
        
        if commit:
            instance.save()
        
        return instance


class ThemeForm(forms.ModelForm):
    """Form untuk upload dan edit Theme"""
    
    class Meta:
        model = Theme
        fields = [
            'name', 'slug', 'description', 'category',
            'zip_file', 'thumbnail',
            'difficulty_level', 'price', 'is_premium', 'is_active'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500',
                'placeholder': 'Nama Tema',
            }),
            'slug': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500',
                'placeholder': 'slug-otomatis-dari-nama',
            }),
            'description': forms.Textarea(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500',
                'rows': 4,
                'placeholder': 'Deskripsi tema...',
            }),
            'category': forms.Select(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500',
            }),
            'zip_file': forms.FileInput(attrs={
                'class': 'block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-semibold file:bg-indigo-50 file:text-indigo-700 hover:file:bg-indigo-100',
                'accept': '.zip',
            }),
            'thumbnail': forms.FileInput(attrs={
                'class': 'block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-semibold file:bg-indigo-50 file:text-indigo-700 hover:file:bg-indigo-100',
                'accept': 'image/*',
            }),
            'difficulty_level': forms.Select(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500',
            }),
            'price': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500',
                'step': '0.01',
                'min': '0',
            }),
            'is_premium': forms.CheckboxInput(attrs={
                'class': 'h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded',
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded',
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set queryset untuk category
        self.fields['category'].queryset = ThemeCategory.objects.filter(is_active=True)
        self.fields['category'].required = False
        
        # ZIP file required hanya untuk create
        if not self.instance.pk:
            self.fields['zip_file'].required = True
        else:
            self.fields['zip_file'].required = False
            self.fields['zip_file'].help_text = 'Kosongkan jika tidak ingin mengubah file ZIP'
    
    def clean_zip_file(self):
        zip_file = self.cleaned_data.get('zip_file')
        
        if zip_file:
            # Validasi extension
            if not zip_file.name.endswith('.zip'):
                raise ValidationError('File harus berformat ZIP (.zip)')
            
            # Validasi size (max 50MB)
            if zip_file.size > 50 * 1024 * 1024:
                raise ValidationError('Ukuran file ZIP maksimal 50MB')
            
            # Validasi isi ZIP
            try:
                with zipfile.ZipFile(zip_file, 'r') as zip_ref:
                    file_list = zip_ref.namelist()
                    
                    # Cek apakah ada file HTML
                    html_files = [f for f in file_list if f.endswith('.html')]
                    if not html_files:
                        raise ValidationError('ZIP file harus berisi minimal satu file HTML (index.html, main.html, atau template.html)')
                    
                    # Cek apakah ada file HTML utama
                    main_html_found = False
                    for html_file in html_files:
                        filename = os.path.basename(html_file)
                        if filename.lower() in ['index.html', 'main.html', 'template.html']:
                            main_html_found = True
                            break
                    
                    if not main_html_found:
                        # Warning jika tidak ada file utama, tapi tetap valid
                        pass
            
            except zipfile.BadZipFile:
                raise ValidationError('File ZIP tidak valid atau corrupt')
            except Exception as e:
                raise ValidationError(f'Error membaca file ZIP: {str(e)}')
        
        return zip_file
    
    def clean_thumbnail(self):
        thumbnail = self.cleaned_data.get('thumbnail')
        
        if thumbnail:
            # Validasi extension
            valid_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp']
            ext = os.path.splitext(thumbnail.name)[1].lower()
            if ext not in valid_extensions:
                raise ValidationError(f'Format gambar tidak didukung. Gunakan: {", ".join(valid_extensions)}')
            
            # Validasi size (max 5MB)
            if thumbnail.size > 5 * 1024 * 1024:
                raise ValidationError('Ukuran thumbnail maksimal 5MB')
        
        return thumbnail

