# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('locations', '0005_auto_20160226_1543'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='gatewaytype',
            options={'ordering': ['name'], 'verbose_name': 'Location Type'},
        ),
    ]
