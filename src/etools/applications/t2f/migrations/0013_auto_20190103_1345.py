# Generated by Django 2.0.9 on 2019-01-03 13:45

from django.db import migrations, models
import etools.applications.t2f.models


class Migration(migrations.Migration):

    dependencies = [
        ('t2f', '0012_auto_20190104_1911'),
    ]

    operations = [
        migrations.AlterField(
            model_name='travelattachment',
            name='file',
            field=models.FileField(blank=True, max_length=255, null=True, upload_to=etools.applications.t2f.models.determine_file_upload_path, verbose_name='File'),
        ),
    ]
