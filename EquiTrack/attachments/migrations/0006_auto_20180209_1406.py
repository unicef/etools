# -*- coding: utf-8 -*-
# Generated by Django 1.9.10 on 2018-02-09 14:06
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('attachments', '0005_auto_20180206_1700'),
    ]

    operations = [
        migrations.AlterField(
            model_name='attachment',
            name='code',
            field=models.CharField(blank=True, max_length=64, verbose_name='Code'),
        ),
    ]
