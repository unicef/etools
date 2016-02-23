# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('partners', '0003_auto_20151012_1321'),
    ]

    operations = [
        migrations.AlterField(
            model_name='agreement',
            name='agreement_number',
            field=models.CharField(help_text='Reference Number', unique=True, max_length=45L, blank=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='agreement',
            name='agreement_type',
            field=models.CharField(max_length=10, choices=[('PCA', 'Partner Cooperation Agreement'), ('SSFA', 'Small Scale Funding Agreement'), ('MOU', 'Memorandum of Understanding'), ('ic', 'Institutional Contract'), ('AWP', 'Work Plan')]),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='partnerorganization',
            name='partner_type',
            field=models.CharField(max_length=50, choices=[('--------', '--------'), ('Government', 'Government'), ('Civil Society Organisation', 'Civil Society Organisation'), ('UN Agency', 'UN Agency'), ('Inter-governmental Organisation', 'Inter-governmental Organisation'), ('Bi-Lateral Organisation', 'Bi-Lateral Organisation')]),
            preserve_default=True,
        ),
    ]
