# -*- coding: utf-8 -*-
# Generated by Django 1.9.10 on 2017-11-03 14:57
from __future__ import unicode_literals

import attachments.models
from django.db import migrations, models
import utils.files.storage


class Migration(migrations.Migration):

    dependencies = [
        ('attachments', '0002_auto_20170824_1319'),
    ]

    operations = [
        migrations.AlterField(
            model_name='attachment',
            name='file',
            field=models.FileField(blank=True, null=True, storage=utils.files.storage.SaveNameDefaultStorage(), upload_to=attachments.models.generate_file_path),
        ),
    ]
