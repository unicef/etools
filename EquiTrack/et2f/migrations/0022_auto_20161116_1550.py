# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('et2f', '0021_auto_20161116_1531'),
    ]

    operations = [
        migrations.AddField(
            model_name='travel',
            name='approved_at',
            field=models.DateTimeField(null=True),
        ),
        migrations.AddField(
            model_name='travel',
            name='rejected_at',
            field=models.DateTimeField(null=True),
        ),
        migrations.AddField(
            model_name='travel',
            name='submitted_at',
            field=models.DateTimeField(null=True),
        ),
        migrations.AlterField(
            model_name='costassignment',
            name='grant',
            field=models.ForeignKey(related_name='+', to='et2f.Grant'),
        ),
        migrations.AlterField(
            model_name='costassignment',
            name='wbs',
            field=models.ForeignKey(related_name='+', to='et2f.WBS'),
        ),
        migrations.AlterField(
            model_name='grant',
            name='wbs',
            field=models.ForeignKey(related_name='grants', to='et2f.WBS'),
        ),
    ]
