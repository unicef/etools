# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import filer.fields.file
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0001_initial'),
        ('filer', '0002_auto_20150606_2003'),
        ('trips', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('contenttypes', '0001_initial'),
        ('partners', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='trip',
            name='office',
            field=models.ForeignKey(blank=True, to='users.Office', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='trip',
            name='owner',
            field=models.ForeignKey(related_name='trips', verbose_name=b'Traveller', to=settings.AUTH_USER_MODEL),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='trip',
            name='partners',
            field=models.ManyToManyField(to='partners.PartnerOrganization', null=True, blank=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='trip',
            name='pcas',
            field=models.ManyToManyField(to='partners.PCA', null=True, verbose_name='Related Partnerships', blank=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='trip',
            name='programme_assistant',
            field=models.ForeignKey(related_name='managed_trips', blank=True, to=settings.AUTH_USER_MODEL, help_text=b'Needed if a Travel Authorisation (TA) is required', null=True, verbose_name=b'Staff Responsible for TA'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='trip',
            name='representative',
            field=models.ForeignKey(related_name='approved_trips', blank=True, to=settings.AUTH_USER_MODEL, null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='trip',
            name='section',
            field=models.ForeignKey(blank=True, to='users.Section', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='trip',
            name='supervisor',
            field=models.ForeignKey(related_name='supervised_trips', to=settings.AUTH_USER_MODEL),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='trip',
            name='travel_assistant',
            field=models.ForeignKey(related_name='organised_trips', verbose_name=b'Travel focal point', blank=True, to=settings.AUTH_USER_MODEL, null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='trip',
            name='vision_approver',
            field=models.ForeignKey(verbose_name=b'VISION Approver', blank=True, to=settings.AUTH_USER_MODEL, null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='travelroutes',
            name='trip',
            field=models.ForeignKey(to='trips.Trip'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='fileattachment',
            name='content_type',
            field=models.ForeignKey(blank=True, to='contenttypes.ContentType', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='fileattachment',
            name='file',
            field=filer.fields.file.FilerFileField(blank=True, to='filer.File', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='fileattachment',
            name='trip',
            field=models.ForeignKey(related_name='files', blank=True, to='trips.Trip', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='fileattachment',
            name='type',
            field=models.ForeignKey(to='partners.FileType'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='actionpoint',
            name='person_responsible',
            field=models.ForeignKey(related_name='for_action', to=settings.AUTH_USER_MODEL),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='actionpoint',
            name='trip',
            field=models.ForeignKey(to='trips.Trip'),
            preserve_default=True,
        ),
    ]
