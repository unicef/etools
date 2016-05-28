# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('partners', '0046_auto_20160426_1521'),
    ]

    operations = [
        migrations.AddField(
            model_name='partnerorganization',
            name='last_assessment_date',
            field=models.DateField(null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='assessment',
            name='type',
            field=models.CharField(max_length=50, choices=[('Micro Assessment', 'Micro Assessment'), ('Simplified Checklist', 'Simplified Checklist'), ('Scheduled Audit report', 'Scheduled Audit report'), ('Special Audit report', 'Special Audit report'), ('High Risk Assumed', 'High Risk Assumed'), ('Other', 'Other')]),
        ),
    ]
