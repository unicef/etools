# Generated by Django 3.2.19 on 2024-07-19 11:57

from django.db import migrations, models
import django.utils.timezone
import etools.libraries.pythonlib.datetime
import etools.libraries.pythonlib.encoders
import model_utils.fields


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='AggregateHact',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('year', models.IntegerField(default=etools.libraries.pythonlib.datetime.get_current_year, unique=True, verbose_name='Year')),
                ('partner_values', models.JSONField(blank=True, encoder=etools.libraries.pythonlib.encoders.CustomJSONEncoder, null=True, verbose_name='Partner Values')),
            ],
            options={
                'verbose_name_plural': 'Aggregate hact',
            },
        ),
        migrations.CreateModel(
            name='HactHistory',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('year', models.IntegerField(default=etools.libraries.pythonlib.datetime.get_current_year, verbose_name='Year')),
                ('partner_values', models.JSONField(blank=True, encoder=etools.libraries.pythonlib.encoders.CustomJSONEncoder, null=True, verbose_name='Partner Values')),
            ],
            options={
                'verbose_name_plural': 'Hact Histories',
            },
        ),
    ]
