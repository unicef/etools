# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('partners', '0060_auto_20160721_2313'),
    ]

    operations = [
        migrations.AddField(
            model_name='partnerorganization',
            name='hidden',
            field=models.BooleanField(default=False),
        ),
    ]
