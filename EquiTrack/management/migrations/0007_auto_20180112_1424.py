# -*- coding: utf-8 -*-
# Generated by Django 1.9.10 on 2018-01-12 14:24
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('management', '0006_delete_issuecheckconfig'),
    ]

    operations = [
        migrations.AlterField(
            model_name='flaggedissue',
            name='issue_category',
            field=models.CharField(choices=[('data', 'Data Issue'), ('compliance', 'Compliance Issue')], db_index=True, default='data', max_length=32),
        ),
        migrations.AlterField(
            model_name='flaggedissue',
            name='issue_id',
            field=models.CharField(db_index=True, help_text='A readable ID associated with the specific issue, e.g. "pca-no-attachment"', max_length=100),
        ),
        migrations.AlterField(
            model_name='flaggedissue',
            name='issue_status',
            field=models.CharField(choices=[('new', 'New (untriaged)'), ('pending', 'Pending (triaged, not resolved)'), ('reactivated', 'Reactivated (was resolved but not fixed)'), ('resolved', 'Resolved')], db_index=True, default='new', max_length=32),
        ),
    ]
