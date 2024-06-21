# Generated by Django 3.2.19 on 2024-06-21 08:07

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import model_utils.fields


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('last_mile', '0004_alter_item_options'),
    ]

    operations = [
        migrations.CreateModel(
            name='TransferEvidence',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('comment', models.TextField(blank=True, null=True)),
                ('transfer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='transfer_evidences', to='last_mile.transfer')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='transfer_evidences', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ('-created',),
            },
        ),
    ]
