# -*- coding: utf-8 -*-
# Generated by Django 1.9.10 on 2017-04-25 15:09
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('t2f', '0012_auto_20170425_1509'),
    ]

    operations = [
        migrations.RenameField(
            model_name='iteneraryitem',
            old_name='destination',
            new_name='destination_old',
        ),
        migrations.RenameField(
            model_name='iteneraryitem',
            old_name='origin',
            new_name='origin_old',
        ),
    ]
