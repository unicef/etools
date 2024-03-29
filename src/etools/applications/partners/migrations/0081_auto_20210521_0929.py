# Generated by Django 2.2.7 on 2021-05-21 09:29

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('partners', '0080_merge_20210507_1443'),
    ]

    operations = [
        migrations.AddField(
            model_name='interventionbudget',
            name='partner_supply_local',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=20, verbose_name='Partner Supplies Local'),
        ),
        migrations.AddField(
            model_name='interventionbudget',
            name='total_partner_contribution_local',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=20, verbose_name='Total Partner Contribution'),
        ),
        migrations.AddField(
            model_name='interventionsupplyitem',
            name='provided_by',
            field=models.CharField(choices=[('unicef', 'UNICEF'), ('partner', 'Partner')], default='unicef', max_length=10, verbose_name='Provided By'),
        ),
    ]
