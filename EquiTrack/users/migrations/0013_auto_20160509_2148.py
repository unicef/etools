# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0012_country_vision_last_synced'),
    ]

    operations = [
        migrations.AddField(
            model_name='country',
            name='offices',
            field=models.ManyToManyField(related_name='offices', to='users.Office'),
        ),
        migrations.AddField(
            model_name='country',
            name='sections',
            field=models.ManyToManyField(related_name='sections', to='users.Section'),
        ),
    ]
