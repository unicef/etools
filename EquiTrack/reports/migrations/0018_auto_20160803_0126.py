# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.contrib.postgres.fields
import django.contrib.postgres.fields.hstore


class Migration(migrations.Migration):

    dependencies = [
        ('reports', '0017_auto_20160428_1033'),
    ]

    operations = [
        migrations.AddField(
            model_name='result',
            name='assumptions',
            field=models.TextField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name='result',
            name='labels',
            field=django.contrib.postgres.fields.ArrayField(default=list, base_field=models.CharField(blank=True, max_length=255, null=True, choices=[(b'label1', b'label1'), (b'label2', b'label2'), (b'label3', b'label3')]), size=None),
        ),
        migrations.AddField(
            model_name='result',
            name='metadata',
            field=django.contrib.postgres.fields.hstore.HStoreField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name='result',
            name='sections',
            field=django.contrib.postgres.fields.ArrayField(default=list, base_field=models.CharField(max_length=255, blank=True), size=None),
        ),
        migrations.AddField(
            model_name='result',
            name='status',
            field=models.CharField(blank=True, max_length=255, null=True, choices=[(b'status1', b'status1'), (b'status2', b'status2'), (b'status3', b'status3')]),
        ),
        migrations.AddField(
            model_name='result',
            name='users',
            field=django.contrib.postgres.fields.ArrayField(default=list, base_field=models.IntegerField(), size=None),
        ),
    ]
