# Generated by Django 2.0.8 on 2018-08-14 17:54

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('partners', '0022_remove_intervention_signed_by_unicef'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='fundingcommitment',
            name='grant',
        ),
        migrations.DeleteModel(
            name='FundingCommitment',
        ),
    ]
