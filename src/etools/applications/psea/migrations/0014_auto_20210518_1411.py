# Generated by Django 2.2.20 on 2021-05-18 14:11

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('psea', '0013_auto_20210505_1620'),
    ]

    operations = [
        migrations.AlterField(
            model_name='assessment',
            name='assessment_type',
            field=models.CharField(choices=[('unicef_2020', 'UNICEF Assessment 2020'), ('un_common_other', 'UN Common Assessment- Other UN'), ('un_common_unicef', 'UN Common Assessment- UNICEF')], default='unicef_2020', max_length=16),
        ),
    ]
