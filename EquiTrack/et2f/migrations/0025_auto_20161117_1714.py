# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('et2f', '0024_travel_certification_note'),
    ]

    operations = [
        migrations.AlterField(
            model_name='travel',
            name='purpose',
            field=models.CharField(max_length=500, null=True, blank=True),
        ),
    ]
