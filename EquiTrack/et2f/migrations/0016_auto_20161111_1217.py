# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


def create_initial_fund(apps, schema_editor):
    Fund = apps.get_model('et2f', 'Fund')
    Fund.objects.create(name='Initial fund')


class Migration(migrations.Migration):

    dependencies = [
        ('et2f', '0015_auto_20161111_0129'),
    ]

    operations = [
        migrations.CreateModel(
            name='Fund',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=25)),
            ],
        ),
        migrations.RunPython(create_initial_fund),
        migrations.AddField(
            model_name='costassignment',
            name='fund',
            field=models.ForeignKey(default=1, to='et2f.Fund'),
            preserve_default=False,
        ),
    ]
