# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('trips', '0002_auto_20151004_2225'),
    ]

    operations = [
        migrations.AlterField(
            model_name='trip',
            name='pcas',
            field=models.ManyToManyField(to='partners.PCA', null=True, verbose_name='Related Interventions', blank=True),
            preserve_default=True,
        ),
    ]
