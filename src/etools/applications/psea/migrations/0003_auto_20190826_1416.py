# Generated by Django 2.2.4 on 2019-08-26 14:16

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('psea', '0002_auto_20190820_1618'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='assessor',
            name='focal_points',
        ),
        migrations.AddField(
            model_name='assessment',
            name='focal_points',
            field=models.ManyToManyField(blank=True, related_name='assessor_focal_point', to=settings.AUTH_USER_MODEL, verbose_name='UNICEF Focal Points'),
        ),
    ]
