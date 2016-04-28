# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('trips', '0012_auto_20160425_1243'),
    ]

    operations = [
        migrations.AlterField(
            model_name='trip',
            name='partners',
            field=models.ManyToManyField(to='partners.PartnerOrganization', blank=True),
        ),
        migrations.AlterField(
            model_name='trip',
            name='pcas',
            field=models.ManyToManyField(to='partners.PCA', verbose_name='Related Interventions', blank=True),
        ),
    ]
