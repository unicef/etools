# Generated by Django 3.2.6 on 2022-02-23 12:48

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reports', '0039_auto_20220222_1135'),
    ]

    operations = [
        migrations.AddField(
            model_name='interventionactivity',
            name='is_active',
            field=models.BooleanField(default=True, verbose_name='Is Active'),
        ),
    ]
