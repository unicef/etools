# Generated by Django 3.2.19 on 2024-05-07 10:59

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('audit', '0030_engagement_send_back_comment'),
    ]

    operations = [
        migrations.AlterField(
            model_name='engagement',
            name='end_date',
            field=models.DateField(blank=True, null=True, verbose_name='Start date of first reporting FACE'),
        ),
        migrations.AlterField(
            model_name='engagement',
            name='start_date',
            field=models.DateField(blank=True, null=True, verbose_name='End date of last reporting FACE'),
        ),
    ]
