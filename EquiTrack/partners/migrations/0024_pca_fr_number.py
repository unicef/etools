# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('partners', '0023_auto_20160228_0002'),
    ]

    operations = [
        migrations.AddField(
            model_name='pca',
            name='fr_number',
            field=models.CharField(max_length=50, null=True, blank=True),
        ),
    ]
