# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reports', '0020_indicator_assumptions'),
    ]

    operations = [
        migrations.CreateModel(
            name='CountryProgramme',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=150)),
                ('wbs', models.CharField(unique=True, max_length=30)),
                ('from_date', models.DateField()),
                ('to_date', models.DateField()),
            ],
        ),
        migrations.AlterField(
            model_name='result',
            name='result_structure',
            field=models.ForeignKey(blank=True, to='reports.ResultStructure', null=True),
        ),
        migrations.AlterField(
            model_name='resulttype',
            name='name',
            field=models.CharField(unique=True, max_length=150, choices=[(b'Outcome', b'Outcome'), (b'Output', b'Output'), (b'Activity', b'Activity'), (b'Sub-Activity', b'Sub-Activity')]),
        ),
        migrations.AlterUniqueTogether(
            name='indicator',
            unique_together=set([]),
        ),
        migrations.AddField(
            model_name='result',
            name='country_programme',
            field=models.ForeignKey(blank=True, to='reports.CountryProgramme', null=True),
        ),
        migrations.AddField(
            model_name='resultstructure',
            name='country_programme',
            field=models.ForeignKey(blank=True, to='reports.CountryProgramme', null=True),
        ),
    ]
