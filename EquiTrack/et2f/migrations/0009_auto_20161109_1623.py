# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('et2f', '0008_auto_20161109_1442'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='iteneraryitem',
            name='airline',
        ),
        migrations.AddField(
            model_name='iteneraryitem',
            name='airlines',
            field=models.ManyToManyField(related_name='_iteneraryitem_airlines_+', to='et2f.AirlineCompany'),
        ),
        migrations.AlterField(
            model_name='travel',
            name='currency',
            field=models.ForeignKey(related_name='+', blank=True, to='et2f.Currency', null=True),
        ),
    ]
