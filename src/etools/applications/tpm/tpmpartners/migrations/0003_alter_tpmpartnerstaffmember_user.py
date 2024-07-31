# Generated by Django 4.2.3 on 2024-07-24 19:12

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('tpmpartners', '0002_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='tpmpartnerstaffmember',
            name='user',
            field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='%(app_label)s_%(class)s', to=settings.AUTH_USER_MODEL, verbose_name='User'),
        ),
    ]
