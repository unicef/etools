# -*- coding: utf-8 -*-
# Generated by Django 1.9.10 on 2017-04-21 16:49
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tpm', '0012_merge'),
    ]

    operations = [
        migrations.AlterField(
            model_name='tpmpartnerstaffmember',
            name='email',
            field=models.CharField(max_length=128L, unique=True),
        ),
        migrations.AlterField(
            model_name='tpmpartnerstaffmember',
            name='first_name',
            field=models.CharField(max_length=64L),
        ),
        migrations.AlterField(
            model_name='tpmpartnerstaffmember',
            name='last_name',
            field=models.CharField(max_length=64L),
        ),
    ]
