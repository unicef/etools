# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('funds', '0003_grant_description'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='grant',
            unique_together=set([('donor', 'name')]),
        ),
    ]
