# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('trips', '0008_auto_20151102_2052'),
    ]

    operations = [
        migrations.AddField(
            model_name='trip',
            name='pending_ta_amendment',
            field=models.BooleanField(default=False),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='trip',
            name='submitted_email_sent',
            field=models.BooleanField(default=False),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='trip',
            name='ta_drafted',
            field=models.BooleanField(default=False, help_text=b'Has the TA been drafted in vision if applicable?', verbose_name=b'TA drafted?'),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='trip',
            name='ta_drafted_date',
            field=models.DateField(null=True, verbose_name=b'TA drafted date', blank=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='trip',
            name='ta_reference',
            field=models.CharField(max_length=254, null=True, verbose_name=b'TA reference', blank=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='trip',
            name='ta_required',
            field=models.BooleanField(default=False, help_text=b'Is a Travel Authorisation (TA) is required?', verbose_name=b'TA required?'),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='trip',
            name='ta_trip_took_place_as_planned',
            field=models.BooleanField(default=False, help_text=b'I certify that the travel took place exactly as per the attached Travel Authorization and that there were no changes to the itinerary', verbose_name=b'TA trip took place as attached'),
            preserve_default=True,
        ),
    ]
