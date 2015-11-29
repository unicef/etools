# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='country_override',
            field=models.ForeignKey(related_name='country_override', blank=True, to='users.Country', null=True),
            preserve_default=True,
        ),
    ]
