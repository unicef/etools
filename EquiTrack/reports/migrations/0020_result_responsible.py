# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0014_auto_20160816_2228'),
        ('reports', '0019_auto_20160825_1857'),
    ]

    operations = [
        migrations.AddField(
            model_name='result',
            name='responsible',
            field=models.ForeignKey(blank=True, to='users.UserProfile', null=True),
        ),
    ]
