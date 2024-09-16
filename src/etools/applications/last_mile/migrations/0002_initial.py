# Generated by Django 3.2.19 on 2024-07-19 11:57

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('last_mile', '0001_initial'),
        ('partners', '0001_initial'),
        ('locations', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='transferevidence',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='transfer_evidences', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='transfer',
            name='checked_in_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='transfer_checked_in', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='transfer',
            name='checked_out_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='transfer_checked_out', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='transfer',
            name='destination_point',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='destination_transfers', to='last_mile.pointofinterest'),
        ),
        migrations.AddField(
            model_name='transfer',
            name='origin_point',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='origin_transfers', to='last_mile.pointofinterest'),
        ),
        migrations.AddField(
            model_name='transfer',
            name='origin_transfer',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='following_transfers', to='last_mile.transfer'),
        ),
        migrations.AddField(
            model_name='transfer',
            name='partner_organization',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='partners.partnerorganization'),
        ),
        migrations.AddField(
            model_name='pointofinterest',
            name='parent',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='points_of_interest', to='locations.location', verbose_name='Parent Location'),
        ),
        migrations.AddField(
            model_name='pointofinterest',
            name='partner_organizations',
            field=models.ManyToManyField(blank=True, related_name='points_of_interest', to='partners.PartnerOrganization'),
        ),
        migrations.AddField(
            model_name='pointofinterest',
            name='poi_type',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='points_of_interest', to='last_mile.pointofinteresttype', verbose_name='Type'),
        ),
        migrations.AddField(
            model_name='partnermaterial',
            name='material',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='partner_material', to='last_mile.material'),
        ),
        migrations.AddField(
            model_name='partnermaterial',
            name='partner_organization',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='partner_material', to='partners.partnerorganization'),
        ),
        migrations.AddField(
            model_name='material',
            name='partner_materials',
            field=models.ManyToManyField(through='last_mile.PartnerMaterial', to='partners.PartnerOrganization'),
        ),
        migrations.AddField(
            model_name='itemtransferhistory',
            name='item',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='last_mile.item'),
        ),
        migrations.AddField(
            model_name='itemtransferhistory',
            name='transfer',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='last_mile.transfer'),
        ),
        migrations.AddField(
            model_name='item',
            name='material',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='items', to='last_mile.material'),
        ),
        migrations.AddField(
            model_name='item',
            name='transfer',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='items', to='last_mile.transfer'),
        ),
        migrations.AddField(
            model_name='item',
            name='transfers_history',
            field=models.ManyToManyField(through='last_mile.ItemTransferHistory', to='last_mile.Transfer'),
        ),
        migrations.AlterUniqueTogether(
            name='partnermaterial',
            unique_together={('partner_organization', 'material')},
        ),
        migrations.AlterUniqueTogether(
            name='itemtransferhistory',
            unique_together={('transfer', 'item')},
        ),
    ]
