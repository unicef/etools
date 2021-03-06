# Generated by Django 2.1.8 on 2019-04-23 19:20

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0009_auto_20190122_1412'),
    ]

    operations = [
        migrations.AlterField(
            model_name='country',
            name='offices',
            field=models.ManyToManyField(blank=True, related_name='offices', to='users.Office', verbose_name='Offices'),
        ),
        migrations.AlterField(
            model_name='country',
            name='threshold_tae_usd',
            field=models.DecimalField(blank=True, decimal_places=4, max_digits=20, null=True, verbose_name='Threshold TAE (USD)'),
        ),
        migrations.AlterField(
            model_name='country',
            name='threshold_tre_usd',
            field=models.DecimalField(blank=True, decimal_places=4, max_digits=20, null=True, verbose_name='Threshold TRE (USD)'),
        ),
    ]
