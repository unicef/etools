# Generated by Django 2.0.9 on 2019-01-22 14:12

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('partners', '0030_assessment_active'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='agreementamendment',
            options={'ordering': ('-created',), 'verbose_name': 'Amendment', 'verbose_name_plural': 'Agreement amendments'},
        ),
        migrations.AlterModelOptions(
            name='interventionamendment',
            options={'verbose_name': 'Amendment', 'verbose_name_plural': 'Intervention amendments'},
        ),
        migrations.AlterModelOptions(
            name='interventionbudget',
            options={'verbose_name_plural': 'Intervention budget'},
        ),
    ]
