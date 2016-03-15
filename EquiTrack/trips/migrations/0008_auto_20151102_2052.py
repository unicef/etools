# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('trips', '0007_auto_20151027_1852'),
    ]

    operations = [
        migrations.AddField(
            model_name='trip',
            name='driver',
            field=models.ForeignKey(related_name='trips_driver', verbose_name=b'Driver', blank=True, to=settings.AUTH_USER_MODEL, null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='trip',
            name='driver_supervisor',
            field=models.ForeignKey(related_name='driver_supervised_trips', verbose_name=b'Supervisor for Driver', blank=True, to=settings.AUTH_USER_MODEL, null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='trip',
            name='driver_trip',
            field=models.ForeignKey(related_name='drivers_trip', blank=True, to='trips.Trip', null=True),
            preserve_default=True,
        ),
    ]
