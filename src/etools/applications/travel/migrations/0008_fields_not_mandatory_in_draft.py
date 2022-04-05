# Generated by Django 3.2.6 on 2022-04-05 09:29

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('reports', '0027_auto_20210714_2147'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('travel', '0007_auto_20220405_0916'),
    ]

    operations = [
        migrations.AlterField(
            model_name='trip',
            name='description',
            field=models.TextField(blank=True, null=True, verbose_name='Description'),
        ),
        migrations.AlterField(
            model_name='trip',
            name='office',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='trips', to='reports.office', verbose_name='Office'),
        ),
        migrations.AlterField(
            model_name='trip',
            name='section',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='trips', to='reports.section', verbose_name='Section'),
        ),
        migrations.AlterField(
            model_name='trip',
            name='supervisor',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='supervised_itineraries', to=settings.AUTH_USER_MODEL, verbose_name='Supervisor'),
        ),
    ]
