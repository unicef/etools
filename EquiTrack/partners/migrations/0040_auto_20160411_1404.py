# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import jsonfield.fields


class Migration(migrations.Migration):

    dependencies = [
        ('partners', '0039_distributionplan_document'),
    ]

    operations = [
        migrations.AddField(
            model_name='partnerorganization',
            name='type_of_assessment',
            field=models.CharField(max_length=50, null=True),
        ),
        migrations.AlterField(
            model_name='assessment',
            name='rating',
            field=models.CharField(default='high', max_length=50, choices=[('high', 'High'), ('significant', 'Significant'), ('medium', 'Medium'), ('low', 'Low')]),
        ),
        migrations.AlterField(
            model_name='distributionplan',
            name='document',
            field=jsonfield.fields.JSONField(null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='recommendation',
            name='level',
            field=models.CharField(max_length=50, verbose_name='Priority Flag', choices=[('high', 'High'), ('significant', 'Significant'), ('medium', 'Medium'), ('low', 'Low')]),
        ),
    ]
