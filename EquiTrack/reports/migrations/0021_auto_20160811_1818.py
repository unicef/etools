# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0013_auto_20160509_2148'),
        ('reports', '0020_auto_20160810_1317'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='result',
            name='sections',
        ),
        migrations.AddField(
            model_name='result',
            name='sections',
            field=models.ManyToManyField(to='users.Section'),
        ),
    ]
