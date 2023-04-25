# Generated by Django 3.2.6 on 2022-10-13 12:41

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('organizations', '0001_initial'),
        ('partners', '0114_remove_partner_org_fields'),
    ]

    operations = [
        migrations.AlterField(
            model_name='partnerorganization',
            name='organization',
            field=models.OneToOneField(default=4, on_delete=django.db.models.deletion.CASCADE, related_name='partner', to='organizations.organization'),
            preserve_default=False,
        ),
    ]
