from django import forms
from django.core.exceptions import ValidationError
from .models import (
    Category, Theme, ThemeColorPalette, FontPairing, MusicLibrary,
    BackgroundAsset, DividerAsset, OpeningAnimation, ThemeSection,
    QuoteLibrary, IconSet, TemplateFeature, ThemeRating, ThemePreview,
    CustomCSS
)


class CategoryForm(forms.ModelForm):
    """Form untuk Category dengan custom handling untuk SummernoteTextField"""
    
    class Meta:
        model = Category
        fields = ['name', 'slug', 'description', 'icon_class', 'cover_image', 'order', 'is_featured', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'slug': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'icon_class': forms.TextInput(attrs={'class': 'form-control'}),
            'cover_image': forms.FileInput(attrs={'class': 'form-control'}),
            'order': forms.NumberInput(attrs={'class': 'form-control'}),
            'is_featured': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def save(self, commit=True):
        """Override save untuk menghindari SummernoteTextField validation"""
        instance = super().save(commit=False)
        
        if commit:
            # Use save_base to bypass full_clean validation
            instance.save_base(raw=False, using=None)
            self.save_m2m()
        
        return instance


class ThemeColorPaletteForm(forms.ModelForm):
    """Form untuk ThemeColorPalette"""
    
    class Meta:
        model = ThemeColorPalette
        fields = '__all__'


class FontPairingForm(forms.ModelForm):
    """Form untuk FontPairing"""
    
    class Meta:
        model = FontPairing
        fields = '__all__'


class MusicLibraryForm(forms.ModelForm):
    """Form untuk MusicLibrary"""
    
    class Meta:
        model = MusicLibrary
        fields = '__all__'


class BackgroundAssetForm(forms.ModelForm):
    """Form untuk BackgroundAsset"""
    
    class Meta:
        model = BackgroundAsset
        fields = '__all__'


class DividerAssetForm(forms.ModelForm):
    """Form untuk DividerAsset"""
    
    class Meta:
        model = DividerAsset
        fields = '__all__'


class OpeningAnimationForm(forms.ModelForm):
    """Form untuk OpeningAnimation"""
    
    class Meta:
        model = OpeningAnimation
        fields = '__all__'


class ThemeSectionForm(forms.ModelForm):
    """Form untuk ThemeSection"""
    
    class Meta:
        model = ThemeSection
        fields = '__all__'


class QuoteLibraryForm(forms.ModelForm):
    """Form untuk QuoteLibrary"""
    
    class Meta:
        model = QuoteLibrary
        fields = '__all__'


class IconSetForm(forms.ModelForm):
    """Form untuk IconSet"""
    
    class Meta:
        model = IconSet
        fields = '__all__'


class TemplateFeatureForm(forms.ModelForm):
    """Form untuk TemplateFeature"""
    
    class Meta:
        model = TemplateFeature
        fields = '__all__'


class ThemeRatingForm(forms.ModelForm):
    """Form untuk ThemeRating"""
    
    class Meta:
        model = ThemeRating
        fields = '__all__'


class ThemePreviewForm(forms.ModelForm):
    """Form untuk ThemePreview"""
    
    class Meta:
        model = ThemePreview
        fields = '__all__'


class CustomCSSForm(forms.ModelForm):
    """Form untuk CustomCSS"""
    
    class Meta:
        model = CustomCSS
        fields = '__all__'

