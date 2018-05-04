# -*- coding: utf-8 -*-
# Generated by Django 1.9.10 on 2018-02-21 12:36
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('vision', '0002_fix_null_values'),
    ]

    operations = [
        migrations.AlterField(
            model_name='visionsynclog',
            name='details',
            field=models.CharField(blank=True, default='', max_length=2048, verbose_name='Details'),
        ),
        migrations.AlterField(
            model_name='visionsynclog',
            name='exception_message',
            field=models.TextField(blank=True, default='', verbose_name='Exception Message'),
        ),
    ]
