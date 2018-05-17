# -*- coding: utf-8 -*-
# Generated by Django 1.10.8 on 2018-05-16 17:39
from __future__ import unicode_literals

import django.contrib.gis.db.models.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('locations', '0003_make_not_nullable'),
    ]

    operations = [
        migrations.AddField(
            model_name='cartodbtable',
            name='remap_table_name',
            field=models.CharField(blank=True, max_length=254, null=True, verbose_name='Remap Table Name'),
        ),
        migrations.AddField(
            model_name='location',
            name='prev_pcode',
            field=models.CharField(db_index=True, max_length=32, null=True, verbose_name='Previous Pcode'),
        ),
        migrations.AddField(
            model_name='location',
            name='prev_name',
            field=models.CharField(max_length=254, null=True, verbose_name='Previous name'),
        ),
        migrations.AddField(
            model_name='location',
            name='prev_geom',
            field=django.contrib.gis.db.models.fields.MultiPolygonField(blank=True, null=True, srid=4326,
                                                                        verbose_name='Previous geo Point'),
        ),
        migrations.AddField(
            model_name='location',
            name='date_remapped',
            field=models.DateTimeField(null=True, verbose_name='Remap date and time'),
        ),
    ]
