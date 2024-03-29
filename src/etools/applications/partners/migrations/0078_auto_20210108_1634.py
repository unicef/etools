# Generated by Django 2.2.7 on 2021-01-08 16:34

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('partners', '0077_auto_20201201_2119'),
    ]

    operations = [
        migrations.AlterField(
            model_name='intervention',
            name='submission_date',
            field=models.DateField(blank=True, help_text='The date the partner submitted complete PD/SPD documents to Unicef', null=True, verbose_name='Document Submission Date by CSO'),
        ),
    ]
