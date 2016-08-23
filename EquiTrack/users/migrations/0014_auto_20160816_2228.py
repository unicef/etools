# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
from decimal import Decimal
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0013_auto_20160509_2148'),
    ]

    operations = [
        migrations.AlterField(
            model_name='country',
            name='latitude',
            field=models.DecimalField(blank=True, null=True, max_digits=8, decimal_places=5, validators=[django.core.validators.MinValueValidator(Decimal('-90')), django.core.validators.MaxValueValidator(Decimal('90'))]),
        ),
        migrations.AlterField(
            model_name='country',
            name='longitude',
            field=models.DecimalField(blank=True, null=True, max_digits=8, decimal_places=5, validators=[django.core.validators.MinValueValidator(Decimal('-180')), django.core.validators.MaxValueValidator(Decimal('180'))]),
        ),
    ]
