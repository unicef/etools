# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('partners', '0004_auto_20151014_0817'),
    ]

    operations = [
        migrations.AddField(
            model_name='partnershipbudget',
            name='year',
            field=models.CharField(max_length=5, null=True, blank=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='agreement',
            name='agreement_type',
            field=models.CharField(max_length=10, choices=[('PCA', 'Programme Cooperation Agreement'), ('SSFA', 'Small Scale Funding Agreement'), ('MOU', 'Memorandum of Understanding'), ('ic', 'Institutional Contract'), ('AWP', 'Work Plan')]),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='partnerorganization',
            name='core_values_assessment',
            field=models.FileField(help_text='Only required for CSO partners', null=True, upload_to=b'partners/core_values/', blank=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='partnerorganization',
            name='type',
            field=models.CharField(default='national', max_length=50, verbose_name='CSO Type', choices=[('international', 'International NGO'), set(['National NGO', 'national']), ('cbo', 'CBO'), (('academic',), 'Academic Institution')]),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='partnershipbudget',
            name='in_kind_amount',
            field=models.IntegerField(default=0, verbose_name=b'UNICEF Supplies'),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='pca',
            name='partnership_type',
            field=models.CharField(default='pd', choices=[('pd', 'Programme Document'), ('shpd', 'Simplified Humanitarian Programme Document'), ('dct', 'Cash Transfer'), ('ssfa', 'SSFA ToR')], max_length=255, blank=True, null=True, verbose_name='Document type'),
            preserve_default=True,
        ),
    ]
