# Generated by Django 3.2.6 on 2023-06-14 08:41

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('partners', '0120_merge_20230502_1523'),
    ]

    operations = [
        migrations.AddField(
            model_name='interventionbudget',
            name='has_unfunded_cash',
            field=models.BooleanField(default=False, verbose_name='Unfunded Cash'),
        ),
        migrations.AddField(
            model_name='interventionbudget',
            name='total_unfunded',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=20, verbose_name='Total Unfunded'),
        ),
        migrations.AddField(
            model_name='interventionbudget',
            name='unfunded_hq_cash',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=20, verbose_name='Unfunded Capacity Strengthening Cash Local'),
        ),
        migrations.AddField(
            model_name='interventionmanagementbudget',
            name='act1_unfunded',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=20, verbose_name='Unfunded amount for In-country management and support staff prorated to their contribution to the programme (representation, planning, coordination, logistics, administration, finance)'),
        ),
        migrations.AddField(
            model_name='interventionmanagementbudget',
            name='act2_unfunded',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=20, verbose_name='Unfunded amount for Operational costs prorated to their contribution to the programme (office space, equipment, office supplies, maintenance)'),
        ),
        migrations.AddField(
            model_name='interventionmanagementbudget',
            name='act3_unfunded',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=20, verbose_name='Unfunded amount for Planning, monitoring, evaluation and communication, prorated to their contribution to the programme (venue, travels, etc.)'),
        ),
        migrations.AddField(
            model_name='interventionmanagementbudgetitem',
            name='unfunded_cash',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=20, verbose_name='Unfunded Cash Local'),
        ),
    ]