# Generated by Django 2.2.7 on 2020-11-19 15:28

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('partners', '0046_auto_20200924_1453'),
    ]

    operations = [
        migrations.AddField(
            model_name='interventionbudget',
            name='partner_contribution_other',
            field=models.TextField(blank=True, verbose_name='Partner Non-Financial Contribution'),
        ),
    ]
