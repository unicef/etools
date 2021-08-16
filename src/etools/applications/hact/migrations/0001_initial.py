# Generated by Django 1.10.8 on 2018-03-26 16:05

import django.utils.timezone
from django.db import migrations, models

import model_utils.fields

import etools.applications.core.urlresolvers


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='AggregateHact',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', model_utils.fields.AutoCreatedField(
                    default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(
                    default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('year', models.IntegerField(
                    default=etools.libraries.pythonlib.datetime.get_current_year, unique=True, verbose_name='Year')),
                ('partner_values', models.JSONField(
                    blank=True, null=True, verbose_name='Partner Values')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='HactHistory',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', model_utils.fields.AutoCreatedField(
                    default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(
                    default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('year', models.IntegerField(default=etools.libraries.pythonlib.datetime.get_current_year, verbose_name='Year')),
                ('partner_values', models.JSONField(
                    blank=True, null=True, verbose_name='Partner Values')),
            ],
            options={
                'verbose_name_plural': 'Hact Histories',
            },
        ),
    ]
