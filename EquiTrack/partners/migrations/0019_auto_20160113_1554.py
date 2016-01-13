# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('partners', '0018_auto_20151211_1528'),
    ]

    operations = [
        migrations.AlterField(
            model_name='gwpcalocation',
            name='locality',
            field=models.ForeignKey(blank=True, to='locations.Locality', null=True),
        ),
        migrations.AlterField(
            model_name='gwpcalocation',
            name='location',
            field=models.ForeignKey(blank=True, to='locations.Location', null=True),
        ),
        migrations.AlterField(
            model_name='gwpcalocation',
            name='region',
            field=models.ForeignKey(to='locations.Region'),
        ),
        migrations.AlterField(
            model_name='resultchain',
            name='indicator',
            field=models.ForeignKey(blank=True, to='reports.Indicator', null=True),
        ),
        migrations.AlterField(
            model_name='resultchain',
            name='result',
            field=models.ForeignKey(to='reports.Result'),
        ),
    ]
