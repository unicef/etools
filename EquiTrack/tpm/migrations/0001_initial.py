# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings
import EquiTrack.mixins


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        # ('partners', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='TPMVisit',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('status', models.CharField(default='planned', max_length=32, choices=[('planned', 'Planned'), ('completed', 'Completed'), ('rescheduled', 'Rescheduled'), ('no-activity', 'No-Activity'), ('discontinued', 'Discontinued')])),
                ('cycle_number', models.PositiveIntegerField(null=True, blank=True)),
                ('tentative_date', models.DateField(null=True, blank=True)),
                ('completed_date', models.DateField(null=True, blank=True)),
                ('comments', models.TextField(null=True, blank=True)),
                ('created_date', models.DateTimeField(auto_now_add=True)),
                ('report', models.FileField(null=True, upload_to='tpm_reports', blank=True)),
                ('assigned_by', models.ForeignKey(to=settings.AUTH_USER_MODEL)),
                ('pca', models.ForeignKey(to='partners.PCA')),
                ('pca_location', models.ForeignKey(blank=True, to='partners.GwPCALocation', null=True)),
            ],
            options={
                'verbose_name': 'TPM Visit',
                'verbose_name_plural': 'TPM Visits',
            },
            bases=(EquiTrack.mixins.AdminURLMixin, models.Model),
        ),
    ]
