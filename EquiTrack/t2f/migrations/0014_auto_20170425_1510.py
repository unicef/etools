# -*- coding: utf-8 -*-
# Generated by Django 1.9.10 on 2017-04-25 15:10
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('t2f', '0013_auto_20170425_1509'),
    ]

    operations = [
        migrations.RenameField(
            model_name='iteneraryitem',
            old_name='destination_fk',
            new_name='destination',
        ),
        migrations.RenameField(
            model_name='iteneraryitem',
            old_name='origin_fk',
            new_name='origin',
        ),
    ]
