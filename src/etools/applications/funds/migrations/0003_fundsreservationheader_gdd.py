# Generated by Django 4.2.3 on 2024-10-10 23:14

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('governments', '0001_initial'),
        ('funds', '0002_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='fundsreservationheader',
            name='gdd',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='frs', to='governments.gdd', verbose_name='Government Digital Document'),
        ),
    ]
