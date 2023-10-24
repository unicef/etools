# Generated by Django 3.2.19 on 2023-10-20 13:21

from django.db import migrations, models
import django.utils.timezone
import model_utils.fields


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='SectionHistory',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('history_type', models.CharField(choices=[('create', 'Create'), ('merge', 'Merge'), ('close', 'Close')], max_length=10, verbose_name='Name')),
            ],
            options={
                'abstract': False,
            },
        ),
    ]
