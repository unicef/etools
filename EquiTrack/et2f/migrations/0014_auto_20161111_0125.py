# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('et2f', '0013_auto_20161110_1544'),
    ]

    operations = [
        migrations.AddField(
            model_name='travel',
            name='canceled_at',
            field=models.DateTimeField(null=True),
        ),
        migrations.AddField(
            model_name='travel',
            name='completed_at',
            field=models.DateTimeField(null=True),
        ),
        migrations.AddField(
            model_name='travel',
            name='rejection_notice',
            field=models.TextField(null=True),
        ),
    ]
