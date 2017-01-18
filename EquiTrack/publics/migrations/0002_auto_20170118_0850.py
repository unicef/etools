# -*- coding: utf-8 -*-
# Generated by Django 1.9.10 on 2017-01-18 06:50
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('publics', '0001_initial'),
        ('t2f', '0011_remove_iteneraryitem_new_airlines'),
    ]

    operations = [
        migrations.CreateModel(
            name='BusinessArea',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=128)),
                ('code', models.CharField(max_length=32)),
            ],
        ),
        migrations.CreateModel(
            name='BusinessRegion',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=16)),
                ('code', models.CharField(max_length=2)),
            ],
        ),
        migrations.CreateModel(
            name='Country',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=64)),
                ('long_name', models.CharField(max_length=128)),
                ('vision_code', models.CharField(max_length=3, null=True)),
                ('iso_2', models.CharField(max_length=2)),
                ('iso_3', models.CharField(max_length=3)),
                ('valid_from', models.DateField()),
                ('valid_to', models.DateField()),
                ('business_area', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='countries', to='publics.BusinessArea')),
                ('currency', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='publics.Currency')),
            ],
        ),
        migrations.AddField(
            model_name='dsaregion',
            name='area_code',
            field=models.CharField(default=1, max_length=3),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='dsaregion',
            name='area_name',
            field=models.CharField(default=1, max_length=32),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='dsaregion',
            name='new_country',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='dsa_regions', to='publics.Country', null=True),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='businessarea',
            name='region',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='business_areas', to='publics.BusinessRegion'),
        ),
    ]
