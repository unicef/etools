# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import smart_selects.db_fields
import paintstore.fields
import django.contrib.gis.db.models.fields
import locations.models


class Migration(migrations.Migration):

    dependencies = [
        ('contenttypes', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='CartoDBTable',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('domain', models.CharField(max_length=254)),
                ('api_key', models.CharField(max_length=254)),
                ('table_name', models.CharField(max_length=254)),
                ('display_name', models.CharField(max_length=254, null=True, blank=True)),
                ('name_col', models.CharField(default=b'name', max_length=254)),
                ('pcode_col', models.CharField(default=b'pcode', max_length=254)),
                ('parent_code_col', models.CharField(max_length=254, null=True, blank=True)),
                ('color', paintstore.fields.ColorPickerField(default=locations.models.get_random_color, max_length=7, null=True, blank=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='GatewayType',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(unique=True, max_length=64L)),
            ],
            options={
                'ordering': ['name'],
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Governorate',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=45L)),
                ('p_code', models.CharField(max_length=32L, null=True, blank=True)),
                ('color', paintstore.fields.ColorPickerField(default=locations.models.get_random_color, max_length=7, null=True, blank=True)),
                ('geom', django.contrib.gis.db.models.fields.MultiPolygonField(srid=4326, null=True, blank=True)),
                ('gateway', models.ForeignKey(verbose_name=b'Admin type', blank=True, to='locations.GatewayType', null=True)),
            ],
            options={
                'ordering': ['name'],
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='LinkedLocation',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('object_id', models.PositiveIntegerField()),
                ('content_type', models.ForeignKey(to='contenttypes.ContentType')),
                ('governorate', models.ForeignKey(to='locations.Governorate')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Locality',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('cad_code', models.CharField(max_length=11L)),
                ('cas_code', models.CharField(max_length=11L)),
                ('cas_code_un', models.CharField(max_length=11L)),
                ('name', models.CharField(max_length=128L)),
                ('cas_village_name', models.CharField(max_length=128L)),
                ('p_code', models.CharField(max_length=32L, null=True, blank=True)),
                ('color', paintstore.fields.ColorPickerField(default=locations.models.get_random_color, max_length=7, null=True, blank=True)),
                ('geom', django.contrib.gis.db.models.fields.MultiPolygonField(srid=4326, null=True, blank=True)),
                ('gateway', models.ForeignKey(verbose_name=b'Admin type', blank=True, to='locations.GatewayType', null=True)),
            ],
            options={
                'ordering': ['name'],
                'verbose_name': 'Sub-district',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Location',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=254L)),
                ('latitude', models.FloatField(null=True, blank=True)),
                ('longitude', models.FloatField(null=True, blank=True)),
                ('p_code', models.CharField(max_length=32L, null=True, blank=True)),
                ('point', django.contrib.gis.db.models.fields.PointField(srid=4326, null=True, blank=True)),
                ('gateway', models.ForeignKey(verbose_name=b'Gateway type', to='locations.GatewayType')),
                ('locality', models.ForeignKey(to='locations.Locality')),
            ],
            options={
                'ordering': ['name'],
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Region',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=45L)),
                ('p_code', models.CharField(max_length=32L, null=True, blank=True)),
                ('color', paintstore.fields.ColorPickerField(default=locations.models.get_random_color, max_length=7, null=True, blank=True)),
                ('geom', django.contrib.gis.db.models.fields.MultiPolygonField(srid=4326, null=True, blank=True)),
                ('gateway', models.ForeignKey(verbose_name=b'Admin type', blank=True, to='locations.GatewayType', null=True)),
                ('governorate', models.ForeignKey(to='locations.Governorate')),
            ],
            options={
                'ordering': ['name'],
                'verbose_name': 'District',
            },
            bases=(models.Model,),
        ),
        migrations.AlterUniqueTogether(
            name='location',
            unique_together=set([('name', 'gateway', 'p_code')]),
        ),
        migrations.AddField(
            model_name='locality',
            name='region',
            field=models.ForeignKey(to='locations.Region'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='linkedlocation',
            name='locality',
            field=smart_selects.db_fields.ChainedForeignKey(chained_model_field=b'region', chained_field=b'region', blank=True, auto_choose=True, to='locations.Locality', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='linkedlocation',
            name='location',
            field=smart_selects.db_fields.ChainedForeignKey(chained_model_field=b'locality', chained_field=b'locality', blank=True, to='locations.Location', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='linkedlocation',
            name='region',
            field=smart_selects.db_fields.ChainedForeignKey(chained_model_field=b'governorate', chained_field=b'governorate', auto_choose=True, to='locations.Region'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='cartodbtable',
            name='location_type',
            field=models.ForeignKey(to='locations.GatewayType'),
            preserve_default=True,
        ),
    ]
