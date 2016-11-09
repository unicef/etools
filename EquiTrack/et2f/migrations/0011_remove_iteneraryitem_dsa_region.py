# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('et2f', '0010_dsaregion'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='iteneraryitem',
            name='dsa_region',
        ),
        migrations.AddField(
            model_name='iteneraryitem',
            name='dsa_region',
            field=models.ForeignKey(related_name='+', default=1, to='et2f.DSARegion'),
            preserve_default=False,
        ),
    ]
