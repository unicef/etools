# -*- coding: utf-8 -*-
# Generated by Django 1.10.8 on 2018-03-21 09:14
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('action_points', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='actionpoint',
            name='high_priority',
            field=models.BooleanField(default=False, verbose_name='High Priority'),
        ),
    ]
