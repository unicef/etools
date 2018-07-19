# -*- coding: utf-8 -*-
# Generated by Django 1.10.8 on 2018-07-19 18:14
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('partners', '0018_auto_20180717_1536'),
    ]

    operations = [
        migrations.AddField(
            model_name='intervention',
            name='signed_by_unicef',
            field=models.BooleanField(default=False, verbose_name='Signed By UNICEF Authorized Officer'),
        ),
    ]
