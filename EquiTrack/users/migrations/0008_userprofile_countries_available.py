# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0007_auto_20160205_2230'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='countries_available',
            field=models.ManyToManyField(related_name='accessible_by', to='users.Country'),
        ),
    ]
