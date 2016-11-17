# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('et2f', '0023_travelattachment'),
    ]

    operations = [
        migrations.AddField(
            model_name='travel',
            name='certification_note',
            field=models.TextField(null=True),
        ),
    ]
