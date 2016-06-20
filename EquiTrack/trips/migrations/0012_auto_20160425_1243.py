# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import trips.models


class Migration(migrations.Migration):

    dependencies = [
        ('trips', '0011_linkedpartner'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='fileattachment',
            name='file',
        ),
        migrations.AlterField(
            model_name='fileattachment',
            name='report',
            field=models.FileField(max_length=255, upload_to=trips.models.get_report_filename),
        ),
    ]
