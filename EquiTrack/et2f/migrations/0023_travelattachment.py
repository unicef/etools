# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import et2f.models


class Migration(migrations.Migration):

    dependencies = [
        ('et2f', '0022_auto_20161116_1550'),
    ]

    operations = [
        migrations.CreateModel(
            name='TravelAttachment',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('type', models.CharField(max_length=64)),
                ('name', models.CharField(max_length=255)),
                ('file', models.FileField(upload_to=et2f.models.determine_file_upload_path)),
                ('travel', models.ForeignKey(related_name='attachments', to='et2f.Travel')),
            ],
        ),
    ]
