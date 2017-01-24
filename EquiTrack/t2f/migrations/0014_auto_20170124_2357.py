# -*- coding: utf-8 -*-
# Generated by Django 1.9.10 on 2017-01-24 21:57
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('t2f', '0013_auto_20170123_1417'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='travelactivity',
            name='primary_traveler',
        ),
        migrations.AlterField(
            model_name='travelactivity',
            name='partnership',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='+', to='partners.Intervention'),
        ),

        migrations.AddField(
            model_name='travelactivity',
            name='primary_traveler',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL),
        ),
    ]
