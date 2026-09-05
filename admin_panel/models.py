from django.db import models
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.utils import timezone
import json

# Create your models here.

class ActivityLog(models.Model):
    """Log aktivitas admin untuk audit trail"""
    ACTION_CHOICES = [
        ('create', 'Created'),
        ('update', 'Updated'),
        ('delete', 'Deleted'),
        ('view', 'Viewed'),
        ('login', 'Logged In'),
        ('logout', 'Logged Out'),
        ('export', 'Exported'),
        ('import', 'Imported'),
        ('approve', 'Approved'),
        ('reject', 'Rejected'),
        ('activate', 'Activated'),
        ('deactivate', 'Deactivated'),
        ('bulk_action', 'Bulk Action'),
    ]
    
    # Actor (siapa yang melakukan)
    actor = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='activity_logs',
        verbose_name="Actor"
    )
    actor_ip = models.GenericIPAddressField(blank=True, null=True, verbose_name="IP Address")
    actor_user_agent = models.TextField(blank=True, verbose_name="User Agent")
    
    # Action (apa yang dilakukan)
    action_type = models.CharField(max_length=20, choices=ACTION_CHOICES, verbose_name="Action Type")
    action_description = models.CharField(max_length=255, verbose_name="Action Description")
    
    # Target (objek yang dikenai aksi) - nullable untuk action seperti login/logout
    target_content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True, related_name='activity_logs_as_target', verbose_name="Target Model")
    target_object_id = models.PositiveIntegerField(null=True, blank=True, verbose_name="Target Object ID")
    target_object = GenericForeignKey('target_content_type', 'target_object_id')
    target_representation = models.CharField(max_length=255, blank=True, verbose_name="Target String Representation")
    
    # Additional data
    changes_data = models.JSONField(blank=True, null=True, verbose_name="Changes Data")
    additional_info = models.JSONField(blank=True, null=True, verbose_name="Additional Information")
    
    # Metadata
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name="Timestamp")
    session_key = models.CharField(max_length=40, blank=True, verbose_name="Session Key")
    
    def __str__(self):
        actor_name = self.actor.username if self.actor else "System"
        return f"{actor_name} {self.get_action_type_display()}: {self.action_description}"
    
    @classmethod
    def log_activity(cls, actor, action_type, target_object, description=None, changes=None, additional_info=None, request=None):
        """Helper method untuk membuat log aktivitas"""
        
        # Auto generate description jika tidak diberikan
        if not description:
            action_display = dict(cls.ACTION_CHOICES).get(action_type, action_type)
            model_name = target_object._meta.verbose_name if target_object else "Object"
            description = f"{action_display} {model_name}: {str(target_object)}"
        
        # Extract request information
        actor_ip = None
        actor_user_agent = ""
        session_key = ""
        
        if request:
            actor_ip = cls.get_client_ip(request)
            actor_user_agent = request.META.get('HTTP_USER_AGENT', '')
            session_key = request.session.session_key or ""
        
        # Handle target_object yang None (untuk login/logout dll)
        target_repr = str(target_object) if target_object else ""
        
        return cls.objects.create(
            actor=actor,
            actor_ip=actor_ip,
            actor_user_agent=actor_user_agent,
            action_type=action_type,
            action_description=description,
            target_object=target_object if target_object else None,
            target_representation=target_repr,
            changes_data=changes,
            additional_info=additional_info,
            session_key=session_key
        )
    
    @staticmethod
    def get_client_ip(request):
        """Get client IP address from request"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
        
    class Meta:
        verbose_name = "Activity Log"
        verbose_name_plural = "Activity Logs"
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['actor', 'timestamp']),
            models.Index(fields=['action_type', 'timestamp']),
            models.Index(fields=['target_content_type', 'target_object_id']),
        ]


# ===== REMOVED MODELS (Not needed for small website) =====
# AdminNotification, AdminPreference, SystemHealth - All removed
