# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('partners', '0043_auto_20160413_1358'),
    ]

    operations = [
        migrations.AddField(
            model_name='pca',
            name='planned_visits',
            field=models.IntegerField(default=0),
        ),
    ]
