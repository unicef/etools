# Generated by Django 3.2.19 on 2024-04-01 10:21

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('partners', '0121_auto_20230814_1058'),
        ('last_mile', '0012_alter_transfer_transfer_type'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='item',
            name='description',
        ),
        migrations.CreateModel(
            name='PartnerMaterial',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('description', models.CharField(max_length=255)),
                ('material', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='partner_material', to='last_mile.material')),
                ('partner_organization', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='partner_material', to='partners.partnerorganization')),
            ],
            options={
                'unique_together': {('partner_organization', 'material')},
            },
        ),
        migrations.AddField(
            model_name='material',
            name='partner_materials',
            field=models.ManyToManyField(through='last_mile.PartnerMaterial', to='partners.PartnerOrganization'),
        ),
    ]
