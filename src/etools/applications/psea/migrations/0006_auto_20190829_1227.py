# Generated by Django 2.2.4 on 2019-08-29 12:27

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('psea', '0005_auto_20190828_1726'),
    ]

    operations = [
        migrations.AlterField(
            model_name='assessor',
            name='assessor_type',
            field=models.CharField(choices=[('external', 'External Individual'), ('staff', 'UNICEF Staff'), ('firm', 'Assessing Firm')], max_length=30, verbose_name='Type'),
        ),
    ]
