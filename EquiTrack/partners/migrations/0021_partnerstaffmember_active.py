# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('partners', '0020_auto_20160127_1751'),
    ]

    operations = [
        migrations.AddField(
            model_name='partnerstaffmember',
            name='active',
            field=models.BooleanField(default=True),
        ),
    ]
