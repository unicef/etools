# Generated by Django 2.2.7 on 2020-07-08 13:28

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('partners', '0043_auto_20200701_1544'),
    ]

    operations = [
        migrations.AddField(
            model_name='intervention',
            name='humanitarian_flag',
            field=models.BooleanField(default=False, verbose_name='Humanitarian'),
        ),
    ]
