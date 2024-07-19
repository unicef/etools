# Generated by Django 3.2.19 on 2024-07-19 11:57

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('unicef_attachments', '0007_alter_attachment_hyperlink'),
    ]

    operations = [
        migrations.CreateModel(
            name='AttachmentFlat',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('partner', models.CharField(blank=True, max_length=255, verbose_name='Partner')),
                ('partner_type', models.CharField(blank=True, max_length=150, verbose_name='Partner Type')),
                ('vendor_number', models.CharField(blank=True, max_length=50, verbose_name='Vendor Number')),
                ('pd_ssfa', models.IntegerField(blank=True, null=True, verbose_name='PD SSFA ID')),
                ('pd_ssfa_number', models.CharField(blank=True, max_length=64, verbose_name='PD SSFA Number')),
                ('agreement_reference_number', models.CharField(blank=True, max_length=100, verbose_name='Agreement Reference Number')),
                ('object_link', models.URLField(blank=True, verbose_name='Object Link')),
                ('file_type', models.CharField(blank=True, max_length=100, verbose_name='File Type')),
                ('file_link', models.CharField(blank=True, max_length=1024, verbose_name='File Link')),
                ('filename', models.CharField(blank=True, max_length=1024, verbose_name='File Name')),
                ('source', models.CharField(blank=True, max_length=150, verbose_name='Source')),
                ('uploaded_by', models.CharField(blank=True, max_length=255, verbose_name='Uploaded by')),
                ('created', models.DateTimeField(null=True, verbose_name='Created')),
                ('ip_address', models.GenericIPAddressField(default='0.0.0.0')),
                ('attachment', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='denormalized', to='unicef_attachments.attachment')),
            ],
        ),
    ]
