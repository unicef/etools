# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0009_countries_available'),
    ]

    operations = [
        migrations.AddField(
            model_name='country',
            name='initial_zoom',
            field=models.IntegerField(default=8),
        ),
        migrations.AddField(
            model_name='country',
            name='latitude',
            field=models.DecimalField(null=True, max_digits=8, decimal_places=6, blank=True),
        ),
        migrations.AddField(
            model_name='country',
            name='longitude',
            field=models.DecimalField(null=True, max_digits=8, decimal_places=6, blank=True),
        ),
    ]
