# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('et2f', '0019_auto_20161115_1805'),
    ]

    operations = [
        migrations.AddField(
            model_name='travel',
            name='cancellation_note',
            field=models.TextField(null=True),
        ),
    ]
