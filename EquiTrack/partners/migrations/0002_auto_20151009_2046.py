# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('partners', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='partnerorganization',
            name='core_values_assessment',
            field=models.FileField(upload_to=b'partners/core_values/', null=True, verbose_name='Date positively assessed against core values', blank=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='partnerorganization',
            name='partner_type',
            field=models.CharField(max_length=50, choices=[('Government', 'Government'), ('Civil Society Organisation', 'Civil Society Organisation'), ('UN Agency', 'UN Agency'), ('Inter-governmental Organisation', 'Inter-governmental Organisation'), ('Bi-Lateral Organisation', 'Bi-Lateral Organisation')]),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='partnerorganization',
            name='type',
            field=models.CharField(default='national', max_length=50, verbose_name='CSO Type', choices=[('international', 'International NGO'), set(['national', 'NGO']), ('cbo', 'CBO'), (('academic',), 'Academic Institution')]),
            preserve_default=True,
        ),
    ]
