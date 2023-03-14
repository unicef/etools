# Generated by Django 3.2.6 on 2022-12-13 12:23

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('partners', '0107_auto_20221208_0902'),
    ]

    operations = [
        migrations.AlterField(
            model_name='directcashtransfer',
            name='amount_less_than_3_Months_usd',
            field=models.DecimalField(decimal_places=2, max_digits=20, verbose_name='Amount less than 3 months (USD)'),
        ),
    ]
