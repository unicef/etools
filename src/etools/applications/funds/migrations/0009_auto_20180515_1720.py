# -*- coding: utf-8 -*-
# Generated by Django 1.10.8 on 2018-05-15 17:20
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('funds', '0008_fundsreservationitem_donor'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='fundsreservationitem',
            options={'ordering': ('line_item',)},
        ),
        migrations.AlterField(
            model_name='fundsreservationitem',
            name='line_item',
            field=models.PositiveSmallIntegerField(verbose_name='Line Item'),
        ),
    ]
