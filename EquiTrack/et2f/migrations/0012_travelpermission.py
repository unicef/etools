# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('et2f', '0011_remove_iteneraryitem_dsa_region'),
    ]

    operations = [
        migrations.CreateModel(
            name='TravelPermission',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=128)),
                ('code', models.CharField(max_length=128)),
                ('status', models.CharField(max_length=50, choices=[('planned', 'Planned'), ('submitted', 'Submitted'), ('rejected', 'Rejected'), ('approved', 'Approved'), ('completed', 'Completed'), ('cancelled', 'Cancelled'), ('sent_for_payment', 'Sent for payment'), ('done', 'Done'), ('certification_submitted', 'Certification submitted'), ('certification_approved', 'Certification approved'), ('certification_rejected', 'Certification rejected'), ('certified', 'Certified'), ('completed', 'Completed')])),
                ('user_type', models.CharField(max_length=25, choices=[('God', 'God'), ('Anyone', 'Anyone'), ('Traveler', 'Traveler'), ('Travel Administrator', 'Travel Administrator'), ('Supervisor', 'Supervisor'), ('Travel Focal Point', 'Travel Focal Point'), ('Finance Focal Point', 'Finance Focal Point'), ('Representative', 'Representative')])),
                ('value', models.BooleanField(default=False)),
            ],
        ),
    ]
