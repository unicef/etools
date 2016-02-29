# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('funds', '0002_grant_expiry'),
        ('partners', '0022_auto_20160223_2222'),
    ]

    operations = [
        migrations.CreateModel(
            name='DirectCashTransfer',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('fc_ref', models.CharField(max_length=50)),
                ('amount_usd', models.DecimalField(max_digits=10, decimal_places=2)),
                ('liquidation_usd', models.DecimalField(max_digits=10, decimal_places=2)),
                ('outstanding_balance_usd', models.DecimalField(max_digits=10, decimal_places=2)),
                ('amount_less_than_3_Months_usd', models.DecimalField(max_digits=10, decimal_places=2)),
                ('amount_3_to_6_months_usd', models.DecimalField(max_digits=10, decimal_places=2)),
                ('amount_6_to_9_months_usd', models.DecimalField(max_digits=10, decimal_places=2)),
                ('amount_more_than_9_Months_usd', models.DecimalField(max_digits=10, decimal_places=2)),
            ],
        ),
        migrations.CreateModel(
            name='FundingCommitment',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('fr_number', models.CharField(max_length=50)),
                ('wbs', models.CharField(max_length=50)),
                ('fc_type', models.CharField(max_length=50)),
                ('fc_ref', models.CharField(max_length=50)),
                ('fr_item_amount_usd', models.DecimalField(max_digits=10, decimal_places=2)),
                ('agreement_amount', models.DecimalField(max_digits=10, decimal_places=2)),
                ('commitment_amount', models.DecimalField(max_digits=10, decimal_places=2)),
                ('expenditure_amount', models.DecimalField(max_digits=10, decimal_places=2)),
                ('grant', models.ForeignKey(to='funds.Grant')),
            ],
        ),
        migrations.AlterModelOptions(
            name='pca',
            options={'ordering': ['-created_at'], 'verbose_name': 'Intervention', 'verbose_name_plural': 'Interventions'},
        ),
        migrations.RemoveField(
            model_name='partnerorganization',
            name='type',
        ),
        migrations.AddField(
            model_name='partnerorganization',
            name='cso_type',
            field=models.CharField(blank=True, max_length=50, null=True, verbose_name='CSO Type', choices=[('International', 'International'), ('National', 'National'), ('Community Based Organisation', 'Community Based Organisation'), ('Academic Institution', 'Academic Institution')]),
        ),
        migrations.AddField(
            model_name='partnerorganization',
            name='vision_synced',
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name='partnerorganization',
            name='partner_type',
            field=models.CharField(max_length=50, choices=[('Bilateral / Multilateral', 'Bilateral / Multilateral'), ('Civil Society Organization', 'Civil Society Organization'), ('Government', 'Government'), ('UN Agency', 'UN Agency')]),
        ),
        migrations.AddField(
            model_name='fundingcommitment',
            name='intervention',
            field=models.ForeignKey(to='partners.PCA', null=True),
        ),
    ]
