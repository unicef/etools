# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('et2f', '0012_travelpermission'),
    ]

    operations = [
        migrations.AddField(
            model_name='travelpermission',
            name='field',
            field=models.CharField(default='', max_length=64),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='travelpermission',
            name='model',
            field=models.CharField(default='', max_length=128),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='travelpermission',
            name='permission_type',
            field=models.CharField(default='', max_length=5, choices=[(b'edit', b'Edit'), (b'view', b'View')]),
            preserve_default=False,
        ),
    ]
