# Generated by Django 2.2.1 on 2019-06-18 20:20

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('funds', '0010_fundsreservationheader_completed_flag'),
    ]

    operations = [
        migrations.AddField(
            model_name='fundsreservationheader',
            name='delegated',
            field=models.BooleanField(default=False, verbose_name='FR delegated from another CO'),
        ),
    ]
