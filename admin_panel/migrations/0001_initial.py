# Generated manually for admin_panel
from django.conf import settings
import django.contrib.contenttypes.fields
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('contenttypes', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='ActivityLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('actor_ip', models.GenericIPAddressField(blank=True, null=True, verbose_name='IP Address')),
                ('actor_user_agent', models.TextField(blank=True, verbose_name='User Agent')),
                ('action_type', models.CharField(choices=[('create', 'Created'), ('update', 'Updated'), ('delete', 'Deleted'), ('view', 'Viewed'), ('login', 'Logged In'), ('logout', 'Logged Out'), ('export', 'Exported'), ('import', 'Imported'), ('approve', 'Approved'), ('reject', 'Rejected'), ('activate', 'Activated'), ('deactivate', 'Deactivated'), ('bulk_action', 'Bulk Action')], max_length=20, verbose_name='Action Type')),
                ('action_description', models.CharField(max_length=255, verbose_name='Action Description')),
                ('target_object_id', models.PositiveIntegerField(verbose_name='Target Object ID')),
                ('target_representation', models.CharField(blank=True, max_length=255, verbose_name='Target String Representation')),
                ('changes_data', models.JSONField(blank=True, null=True, verbose_name='Changes Data')),
                ('additional_info', models.JSONField(blank=True, null=True, verbose_name='Additional Information')),
                ('timestamp', models.DateTimeField(auto_now_add=True, verbose_name='Timestamp')),
                ('session_key', models.CharField(blank=True, max_length=40, verbose_name='Session Key')),
                ('actor', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='activity_logs', to=settings.AUTH_USER_MODEL, verbose_name='Actor')),
                ('target_content_type', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='contenttypes.contenttype', verbose_name='Target Model')),
            ],
            options={
                'verbose_name': 'Activity Log',
                'verbose_name_plural': 'Activity Logs',
                'ordering': ['-timestamp'],
            },
        ),
        migrations.CreateModel(
            name='AdminPreference',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('dashboard_layout', models.CharField(default='default', max_length=20, verbose_name='Dashboard Layout')),
                ('items_per_page', models.PositiveIntegerField(default=25, verbose_name='Items Per Page')),
                ('default_view_mode', models.CharField(choices=[('list', 'List'), ('grid', 'Grid')], default='list', max_length=10, verbose_name='Default View Mode')),
                ('sidebar_collapsed', models.BooleanField(default=False, verbose_name='Sidebar Collapsed')),
                ('email_notifications', models.BooleanField(default=True, verbose_name='Email Notifications')),
                ('browser_notifications', models.BooleanField(default=True, verbose_name='Browser Notifications')),
                ('notification_sound', models.BooleanField(default=False, verbose_name='Notification Sound')),
                ('theme_preference', models.CharField(choices=[('light', 'Light'), ('dark', 'Dark'), ('auto', 'Auto')], default='light', max_length=10, verbose_name='Theme Preference')),
                ('language_code', models.CharField(default='id', max_length=10, verbose_name='Language Code')),
                ('settings_data', models.JSONField(blank=True, default=dict, verbose_name='Additional Settings')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Created At')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Updated At')),
                ('admin_user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL, verbose_name='Admin User')),
            ],
            options={
                'verbose_name': 'Admin Preference',
                'verbose_name_plural': 'Admin Preferences',
            },
        ),
        migrations.CreateModel(
            name='AdminNotification',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=200, verbose_name='Title')),
                ('message', models.TextField(verbose_name='Message')),
                ('notification_type', models.CharField(choices=[('info', 'Information'), ('success', 'Success'), ('warning', 'Warning'), ('error', 'Error'), ('system', 'System Alert'), ('user_action', 'User Action'), ('security', 'Security Alert')], default='info', max_length=20, verbose_name='Type')),
                ('priority', models.CharField(choices=[('low', 'Low'), ('medium', 'Medium'), ('high', 'High'), ('critical', 'Critical')], default='medium', max_length=10, verbose_name='Priority')),
                ('broadcast_to_all_admins', models.BooleanField(default=False, verbose_name='Broadcast to All Admins')),
                ('is_read', models.BooleanField(default=False, verbose_name='Is Read')),
                ('read_at', models.DateTimeField(blank=True, null=True, verbose_name='Read At')),
                ('is_dismissed', models.BooleanField(default=False, verbose_name='Is Dismissed')),
                ('dismissed_at', models.DateTimeField(blank=True, null=True, verbose_name='Dismissed At')),
                ('related_object_id', models.PositiveIntegerField(blank=True, null=True, verbose_name='Related Object ID')),
                ('action_url', models.URLField(blank=True, verbose_name='Action URL')),
                ('expires_at', models.DateTimeField(blank=True, null=True, verbose_name='Expires At')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Created At')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Updated At')),
                ('created_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='created_notifications', to=settings.AUTH_USER_MODEL, verbose_name='Created By')),
                ('recipient', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='admin_notifications', to=settings.AUTH_USER_MODEL, verbose_name='Specific Recipient')),
                ('related_content_type', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='contenttypes.contenttype', verbose_name='Related Model')),
            ],
            options={
                'verbose_name': 'Admin Notification',
                'verbose_name_plural': 'Admin Notifications',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='SystemHealth',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('component_name', models.CharField(max_length=100, verbose_name='Component Name')),
                ('status', models.CharField(choices=[('healthy', 'Healthy'), ('warning', 'Warning'), ('critical', 'Critical'), ('down', 'Down')], max_length=20, verbose_name='Status')),
                ('message', models.TextField(blank=True, verbose_name='Status Message')),
                ('response_time', models.FloatField(blank=True, null=True, verbose_name='Response Time (ms)')),
                ('cpu_usage', models.FloatField(blank=True, null=True, verbose_name='CPU Usage (%)')),
                ('memory_usage', models.FloatField(blank=True, null=True, verbose_name='Memory Usage (%)')),
                ('disk_usage', models.FloatField(blank=True, null=True, verbose_name='Disk Usage (%)')),
                ('metrics_data', models.JSONField(blank=True, default=dict, verbose_name='Additional Metrics')),
                ('checked_at', models.DateTimeField(auto_now=True, verbose_name='Checked At')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Created At')),
            ],
            options={
                'verbose_name': 'System Health',
                'verbose_name_plural': 'System Health',
                'ordering': ['-checked_at'],
            },
        ),
    ]