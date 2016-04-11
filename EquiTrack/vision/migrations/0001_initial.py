# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0012_country_vision_last_synced'),
    ]

    operations = [
        migrations.CreateModel(
            name='VisionSyncLog',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('handler_name', models.CharField(max_length=50)),
                ('total_records', models.IntegerField(default=0)),
                ('total_processed', models.IntegerField(default=0)),
                ('successful', models.BooleanField(default=False)),
                ('exception_message', models.TextField(null=True, blank=True)),
                ('date_processed', models.DateTimeField(auto_now=True)),
                ('country', models.ForeignKey(to='users.Country')),
            ],
        ),
    ]
