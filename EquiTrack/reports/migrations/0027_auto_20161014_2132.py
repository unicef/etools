# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('partners', '0074_auto_20161014_2132'),
        ('reports', '0026_auto_20161013_2034'),
    ]

    operations = [
        migrations.CreateModel(
            name='ResponsePlan',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=150)),
                ('from_date', models.DateField()),
                ('to_date', models.DateField()),
                ('country_programme', models.ForeignKey(blank=True, to='reports.CountryProgramme', null=True)),
            ],
            options={
                'ordering': ['name'],
            },
        ),
        migrations.AlterUniqueTogether(
            name='resultstructure',
            unique_together=set([]),
        ),
        migrations.RemoveField(
            model_name='resultstructure',
            name='country_programme',
        ),
        migrations.RemoveField(
            model_name='goal',
            name='result_structure',
        ),
        migrations.RemoveField(
            model_name='indicator',
            name='result_structure',
        ),
        migrations.RemoveField(
            model_name='result',
            name='result_structure',
        ),
        migrations.DeleteModel(
            name='ResultStructure',
        ),
        migrations.AddField(
            model_name='goal',
            name='humanitarian_response_plan',
            field=models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, blank=True, to='reports.ResponsePlan', null=True),
        ),
        migrations.AddField(
            model_name='indicator',
            name='humanitarian_response_plan',
            field=models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, blank=True, to='reports.ResponsePlan', null=True),
        ),
        migrations.AddField(
            model_name='result',
            name='humanitarian_response_plan',
            field=models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, blank=True, to='reports.ResponsePlan', null=True),
        ),
        migrations.AlterUniqueTogether(
            name='responseplan',
            unique_together=set([('name', 'from_date', 'to_date')]),
        ),
    ]
