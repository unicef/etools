# Generated by Django 3.2.6 on 2022-03-07 13:56

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('travel', '0005_auto_20210617_0044'),
    ]

    operations = [
        migrations.AddField(
            model_name='trip',
            name='not_as_planned',
            field=models.BooleanField(default=False, verbose_name='Trip completed not as planned'),
        ),
    ]