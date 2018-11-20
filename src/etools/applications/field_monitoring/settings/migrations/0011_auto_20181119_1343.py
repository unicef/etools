# -*- coding: utf-8 -*-
# Generated by Django 1.10.8 on 2018-11-19 13:43
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import model_utils.fields


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('field_monitoring_settings', '0010_auto_20181114_1015'),
    ]

    operations = [
        migrations.AddField(
            model_name='logissue',
            name='author',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, related_name='created_logissues', to=settings.AUTH_USER_MODEL, verbose_name='Issue Raised By'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='logissue',
            name='date_of_close',
            field=model_utils.fields.MonitorField(blank=True, default=None, monitor='status', null=True, verbose_name='Date Action Point Completed', when=set(['past'])),
        ),
    ]
