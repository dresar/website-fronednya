from django import forms
from django.contrib.auth.models import User
from .models import (
    ClientProfile, GroomInfo, BrideInfo, MainEvent, ReceptionEvent
)


class ClientProfileForm(forms.ModelForm):
    """Form untuk Profile Klien"""
    class Meta:
        model = ClientProfile
        fields = ['phone_number', 'whatsapp_number', 'address', 'city', 'profile_photo']
        widgets = {
            'phone_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '08xxxxxxxxxx'}),
            'whatsapp_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '08xxxxxxxxxx'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'city': forms.TextInput(attrs={'class': 'form-control'}),
            'profile_photo': forms.FileInput(attrs={'class': 'form-control'}),
        }


class GroomInfoForm(forms.ModelForm):
    """Form untuk Data Mempelai Pria"""
    class Meta:
        model = GroomInfo
        fields = ['full_name', 'nickname', 'main_photo']
        widgets = {
            'full_name': forms.TextInput(attrs={'class': 'form-control'}),
            'nickname': forms.TextInput(attrs={'class': 'form-control'}),
            'main_photo': forms.FileInput(attrs={'class': 'form-control'}),
        }


class BrideInfoForm(forms.ModelForm):
    """Form untuk Data Mempelai Wanita"""
    class Meta:
        model = BrideInfo
        fields = ['full_name', 'nickname', 'main_photo']
        widgets = {
            'full_name': forms.TextInput(attrs={'class': 'form-control'}),
            'nickname': forms.TextInput(attrs={'class': 'form-control'}),
            'main_photo': forms.FileInput(attrs={'class': 'form-control'}),
        }


class MainEventForm(forms.ModelForm):
    """Form untuk Acara Utama (Akad)"""
    class Meta:
        model = MainEvent
        fields = ['event_name', 'event_date', 'start_time', 'end_time', 'timezone', 
                  'venue_name', 'venue_address', 'venue_phone', 'google_maps_url', 'venue_photo', 'special_notes']
        widgets = {
            'event_name': forms.TextInput(attrs={'class': 'form-control'}),
            'event_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'start_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'end_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'timezone': forms.Select(attrs={'class': 'form-control'}),
            'venue_name': forms.TextInput(attrs={'class': 'form-control'}),
            'venue_address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'venue_phone': forms.TextInput(attrs={'class': 'form-control'}),
            'google_maps_url': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://maps.google.com/...'}),
            'venue_photo': forms.FileInput(attrs={'class': 'form-control'}),
            'special_notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class ReceptionEventForm(forms.ModelForm):
    """Form untuk Acara Resepsi"""
    class Meta:
        model = ReceptionEvent
        fields = ['event_name', 'event_date', 'start_time', 'end_time', 'timezone', 
                  'venue_name', 'venue_address', 'venue_phone', 'google_maps_url', 'venue_photo', 
                  'dress_code', 'special_notes']
        widgets = {
            'event_name': forms.TextInput(attrs={'class': 'form-control'}),
            'event_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'start_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'end_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'timezone': forms.Select(attrs={'class': 'form-control'}),
            'venue_name': forms.TextInput(attrs={'class': 'form-control'}),
            'venue_address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'venue_phone': forms.TextInput(attrs={'class': 'form-control'}),
            'google_maps_url': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://maps.google.com/...'}),
            'venue_photo': forms.FileInput(attrs={'class': 'form-control'}),
            'dress_code': forms.TextInput(attrs={'class': 'form-control'}),
            'special_notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }



