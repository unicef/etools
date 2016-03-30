# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.utils.timezone
import model_utils.fields


class Migration(migrations.Migration):

    dependencies = [
        ('partners', '0036_auto_20160328_0122'),
    ]

    operations = [
        migrations.CreateModel(
            name='AgreementAmendmentLog',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, verbose_name='created', editable=False)),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, verbose_name='modified', editable=False)),
                ('type', models.CharField(max_length=50, choices=[(b'Authorised Officers', b'Authorised Officers'), (b'Banking Info', b'Banking Info'), (b'Agreement Changes', b'Agreement Changes'), (b'Additional Clauses', b'Additional Clauses')])),
                ('amended_at', models.DateField(null=True, verbose_name=b'Signed At')),
                ('status', models.CharField(blank=True, max_length=32L, choices=[('in_process', 'In Process'), ('active', 'Active'), ('implemented', 'Implemented'), ('cancelled', 'Cancelled')])),
                ('agreement', models.ForeignKey(related_name='amendments_log', to='partners.Agreement')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.RemoveField(
            model_name='amendmentlog',
            name='amendment_number',
        ),
    ]
