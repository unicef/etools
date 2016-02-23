# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Activity',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('ai_id', models.PositiveIntegerField(unique=True)),
                ('name', models.CharField(max_length=254)),
                ('location_type', models.CharField(max_length=254)),
            ],
            options={
                'verbose_name_plural': 'activities',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Attribute',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('ai_id', models.PositiveIntegerField(unique=True)),
                ('name', models.CharField(max_length=254)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='AttributeGroup',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('ai_id', models.PositiveIntegerField(unique=True)),
                ('name', models.CharField(max_length=254)),
                ('multiple_allowed', models.BooleanField()),
                ('mandatory', models.BooleanField()),
                ('activity', models.ForeignKey(to='activityinfo.Activity')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Database',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('ai_id', models.PositiveIntegerField(unique=True, verbose_name=b'ActivityInfo ID')),
                ('name', models.CharField(max_length=254)),
                ('username', models.CharField(max_length=254)),
                ('password', models.CharField(max_length=254)),
                ('description', models.CharField(max_length=254, null=True)),
                ('country_name', models.CharField(max_length=254, null=True)),
                ('ai_country_id', models.PositiveIntegerField(null=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Indicator',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('ai_id', models.PositiveIntegerField(unique=True)),
                ('name', models.CharField(max_length=254)),
                ('units', models.CharField(max_length=254)),
                ('category', models.CharField(max_length=254, null=True)),
                ('activity', models.ForeignKey(to='activityinfo.Activity')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Partner',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('ai_id', models.PositiveIntegerField(unique=True)),
                ('name', models.CharField(max_length=254)),
                ('full_name', models.CharField(max_length=254, null=True)),
                ('database', models.ForeignKey(to='activityinfo.Database')),
            ],
            options={
                'ordering': ['name'],
            },
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name='attribute',
            name='attribute_group',
            field=models.ForeignKey(to='activityinfo.AttributeGroup'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='activity',
            name='database',
            field=models.ForeignKey(to='activityinfo.Database'),
            preserve_default=True,
        ),
    ]
