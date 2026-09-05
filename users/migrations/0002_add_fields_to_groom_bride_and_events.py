# Generated manually
from django.db import migrations, models
import django_summernote.fields


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0001_initial'),
    ]

    operations = [
        # Add adab_walimah to ReceptionEvent
        migrations.AddField(
            model_name='receptionevent',
            name='adab_walimah',
            field=models.TextField(blank=True, default='', help_text='Panduan adab untuk tamu undangan', verbose_name='Adab Walimah'),
        ),
        # Create PhotoGallery model
        migrations.CreateModel(
            name='PhotoGallery',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(blank=True, max_length=200, verbose_name='Judul Foto')),
                ('photo', models.ImageField(upload_to='photo_gallery/', verbose_name='Foto')),
                ('caption', models.TextField(blank=True, verbose_name='Keterangan')),
                ('order', models.PositiveIntegerField(default=0, verbose_name='Urutan')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Dibuat Pada')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Diupdate Pada')),
                ('client', models.ForeignKey(on_delete=models.CASCADE, to='users.clientprofile', verbose_name='Klien')),
            ],
            options={
                'verbose_name': 'Galeri Foto',
                'verbose_name_plural': 'Galeri Foto',
                'ordering': ['order', '-created_at'],
            },
        ),
        # Create LoveStory model
        migrations.CreateModel(
            name='LoveStory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=200, verbose_name='Judul Cerita')),
                ('story_date', models.DateField(verbose_name='Tanggal Peristiwa')),
                ('story_content', django_summernote.fields.SummernoteTextField(verbose_name='Isi Cerita')),
                ('story_photo', models.ImageField(blank=True, null=True, upload_to='love_story/', verbose_name='Foto Pendukung')),
                ('order', models.PositiveIntegerField(default=0, verbose_name='Urutan')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Dibuat Pada')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Diupdate Pada')),
                ('client', models.ForeignKey(on_delete=models.CASCADE, to='users.clientprofile', verbose_name='Klien')),
            ],
            options={
                'verbose_name': 'Cerita Cinta',
                'verbose_name_plural': 'Cerita Cinta',
                'ordering': ['order', 'story_date'],
            },
        ),
    ]
