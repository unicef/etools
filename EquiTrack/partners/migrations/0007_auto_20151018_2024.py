# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('partners', '0006_auto_20151015_1202'),
    ]

    operations = [
        migrations.AlterField(
            model_name='assessment',
            name='current',
            field=models.BooleanField(default=False, verbose_name='Basis for risk rating'),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='assessment',
            name='expected_budget',
            field=models.IntegerField(null=True, verbose_name='Planned amount', blank=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='assessment',
            name='partner',
            field=models.ForeignKey(related_name='assessments', to='partners.PartnerOrganization'),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='assessment',
            name='requesting_officer',
            field=models.ForeignKey(related_name='requested_assessments', blank=True, to=settings.AUTH_USER_MODEL, null=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='partnerorganization',
            name='type',
            field=models.CharField(blank=True, max_length=50, verbose_name='CSO Type', choices=[('International NGO', 'International NGO'), ('National NGO', 'National NGO'), ('CBO', 'CBO'), ('Academic Institution', 'Academic Institution')]),
            preserve_default=True,
        ),
    ]
