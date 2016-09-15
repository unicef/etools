# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('reports', '0019_auto_20160825_1857'),
        ('workplan', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Workplan',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('status', models.CharField(blank=True, max_length=32, null=True, choices=[(b'On Track', b'On Track'), (b'Constrained', b'Constrained'), (b'No Progress', b'No Progress'), (b'Target Met', b'Target Met')])),
                ('result_structure', models.ForeignKey(to='reports.ResultStructure')),
            ],
        ),
        migrations.AlterField(
            model_name='comment',
            name='author',
            field=models.ForeignKey(related_name='comments', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='comment',
            name='workplan',
            field=models.ForeignKey(related_name='comments', default=0, to='workplan.Workplan'),
            preserve_default=False,
        ),
    ]
