# Generated by Django 4.2.3 on 2024-07-24 19:12

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('locations', '0001_initial'),
        ('activities', '0002_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='activity',
            name='locations',
            field=models.ManyToManyField(related_name='+', to='locations.location', verbose_name='Locations'),
        ),
    ]
