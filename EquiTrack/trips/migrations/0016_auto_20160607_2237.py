# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('trips', '0015_auto_20160526_1916'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='triplocation',
            options={'ordering': ['id']},
        ),
        migrations.AddField(
            model_name='actionpoint',
            name='follow_up',
            field=models.BooleanField(default=False),
        ),
    ]
