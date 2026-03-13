# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('field_monitoring_settings', '0006_question_tooltip'),
    ]

    operations = [
        migrations.CreateModel(
            name='FMDocumentTypeDescription',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True)),
                ('description', models.TextField(blank=True)),
            ],
            options={
                'verbose_name': 'FM Document Type Description',
            },
        ),
    ]
