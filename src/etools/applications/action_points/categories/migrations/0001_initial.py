# Generated by Django 1.10.8 on 2018-07-31 09:22
from __future__ import unicode_literals

import django.utils.timezone
from django.db import migrations, models

import model_utils.fields


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Category',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('order', models.PositiveIntegerField(db_index=True, editable=False)),
                ('module', models.CharField(choices=[('apd', 'Action Points'), ('t2f', 'Trip Management'), ('tpm', 'Third Party Monitoring'), ('audit', 'Financial Assurance')], max_length=10, verbose_name='Module')),
                ('description', models.TextField(verbose_name='Description')),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
            ],
            options={
                'ordering': ('module', 'order'),
            },
        ),
        migrations.AlterUniqueTogether(
            name='category',
            unique_together=set([('description', 'module')]),
        ),
    ]
