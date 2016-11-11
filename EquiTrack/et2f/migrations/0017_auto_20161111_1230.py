# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models

def create_initial_expense_type(apps, schema_editor):
    ExpenseType = apps.get_model('et2f', 'ExpenseType')
    ExpenseType.objects.create(title='Initial', code='initial')


class Migration(migrations.Migration):

    dependencies = [
        ('et2f', '0016_auto_20161111_1217'),
    ]

    operations = [
        migrations.CreateModel(
            name='ExpenseType',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('title', models.CharField(max_length=32)),
                ('code', models.CharField(max_length=16)),
            ],
        ),
        migrations.RemoveField(
            model_name='expense',
            name='type',
        ),
        migrations.RunPython(create_initial_expense_type),
        migrations.AddField(
            model_name='expense',
            name='type',
            field=models.ForeignKey(related_name='+', default=1, to='et2f.ExpenseType'),
            preserve_default=False,
        ),
    ]
