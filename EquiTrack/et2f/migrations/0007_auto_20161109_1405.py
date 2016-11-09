# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('locations', '0006_auto_20160229_1545'),
        ('et2f', '0006_auto_20161109_1234'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='travelactivity',
            name='location',
        ),
        migrations.AddField(
            model_name='travel',
            name='currency',
            field=models.ForeignKey(related_name='+', default=1, to='et2f.Currency'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='travel',
            name='estimated_travel_cost',
            field=models.DecimalField(default=0, max_digits=20, decimal_places=4),
        ),
        migrations.AddField(
            model_name='travelactivity',
            name='locations',
            field=models.ManyToManyField(related_name='_travelactivity_locations_+', to='locations.Location'),
        ),
    ]
