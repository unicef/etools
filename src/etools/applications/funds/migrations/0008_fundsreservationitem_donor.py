# -*- coding: utf-8 -*-
# Generated by Django 1.10.8 on 2018-05-15 14:52
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('funds', '0007_auto_20180418_1830'),
    ]

    operations = [
        migrations.AddField(
            model_name='fundsreservationitem',
            name='donor',
            field=models.CharField(blank=True, max_length=256, null=True, verbose_name='Donor Name'),
        ),
        migrations.AddField(
            model_name='fundsreservationitem',
            name='donor_code',
            field=models.CharField(blank=True, max_length=30, null=True, verbose_name='Donor Code'),
        ),
    ]
