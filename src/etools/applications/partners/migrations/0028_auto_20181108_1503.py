# -*- coding: utf-8 -*-
# Generated by Django 1.10.8 on 2018-11-08 15:03
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('partners', '0027_auto_20180914_1238'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='interventionsectorlocationlink',
            name='intervention',
        ),
        migrations.RemoveField(
            model_name='interventionsectorlocationlink',
            name='locations',
        ),
        migrations.RemoveField(
            model_name='interventionsectorlocationlink',
            name='sector',
        ),
        migrations.DeleteModel(
            name='InterventionSectorLocationLink',
        ),
    ]
