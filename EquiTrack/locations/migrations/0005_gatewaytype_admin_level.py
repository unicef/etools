# -*- coding: utf-8 -*-
# Generated by Django 1.9.10 on 2017-10-18 16:31
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('locations', '0004_auto_20170112_2051'),
    ]

    operations = [
        migrations.AddField(
            model_name='gatewaytype',
            name='admin_level',
            field=models.PositiveSmallIntegerField(null=True, unique=True),
        ),
    ]
