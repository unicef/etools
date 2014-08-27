# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Deleting field 'Region.area'
        db.delete_column(u'locations_region', 'area')

        # Adding field 'Region.p_code'
        db.add_column(u'locations_region', 'p_code',
                      self.gf('django.db.models.fields.CharField')(max_length=32L, null=True, blank=True),
                      keep_default=False)

        # Adding field 'Region.gateway'
        db.add_column(u'locations_region', 'gateway',
                      self.gf('django.db.models.fields.related.ForeignKey')(to=orm['locations.GatewayType'], null=True, blank=True),
                      keep_default=False)

        # Adding field 'Region.geom'
        db.add_column(u'locations_region', 'geom',
                      self.gf('django.contrib.gis.db.models.fields.PolygonField')(null=True, blank=True),
                      keep_default=False)

        # Deleting field 'Locality.area'
        db.delete_column(u'locations_locality', 'area')

        # Adding field 'Locality.p_code'
        db.add_column(u'locations_locality', 'p_code',
                      self.gf('django.db.models.fields.CharField')(max_length=32L, null=True, blank=True),
                      keep_default=False)

        # Adding field 'Locality.gateway'
        db.add_column(u'locations_locality', 'gateway',
                      self.gf('django.db.models.fields.related.ForeignKey')(to=orm['locations.GatewayType'], null=True, blank=True),
                      keep_default=False)

        # Adding field 'Locality.geom'
        db.add_column(u'locations_locality', 'geom',
                      self.gf('django.contrib.gis.db.models.fields.PolygonField')(null=True, blank=True),
                      keep_default=False)

        # Adding field 'CartoDBTable.parent_code_col'
        db.add_column(u'locations_cartodbtable', 'parent_code_col',
                      self.gf('django.db.models.fields.CharField')(max_length=254, null=True, blank=True),
                      keep_default=False)

        # Deleting field 'Governorate.area'
        db.delete_column(u'locations_governorate', 'area')

        # Adding field 'Governorate.p_code'
        db.add_column(u'locations_governorate', 'p_code',
                      self.gf('django.db.models.fields.CharField')(max_length=32L, null=True, blank=True),
                      keep_default=False)

        # Adding field 'Governorate.gateway'
        db.add_column(u'locations_governorate', 'gateway',
                      self.gf('django.db.models.fields.related.ForeignKey')(to=orm['locations.GatewayType'], null=True, blank=True),
                      keep_default=False)

        # Adding field 'Governorate.geom'
        db.add_column(u'locations_governorate', 'geom',
                      self.gf('django.contrib.gis.db.models.fields.PolygonField')(null=True, blank=True),
                      keep_default=False)


    def backwards(self, orm):
        # Adding field 'Region.area'
        db.add_column(u'locations_region', 'area',
                      self.gf('django.contrib.gis.db.models.fields.PolygonField')(null=True, blank=True),
                      keep_default=False)

        # Deleting field 'Region.p_code'
        db.delete_column(u'locations_region', 'p_code')

        # Deleting field 'Region.gateway'
        db.delete_column(u'locations_region', 'gateway_id')

        # Deleting field 'Region.geom'
        db.delete_column(u'locations_region', 'geom')

        # Adding field 'Locality.area'
        db.add_column(u'locations_locality', 'area',
                      self.gf('django.contrib.gis.db.models.fields.PolygonField')(null=True, blank=True),
                      keep_default=False)

        # Deleting field 'Locality.p_code'
        db.delete_column(u'locations_locality', 'p_code')

        # Deleting field 'Locality.gateway'
        db.delete_column(u'locations_locality', 'gateway_id')

        # Deleting field 'Locality.geom'
        db.delete_column(u'locations_locality', 'geom')

        # Deleting field 'CartoDBTable.parent_code_col'
        db.delete_column(u'locations_cartodbtable', 'parent_code_col')

        # Adding field 'Governorate.area'
        db.add_column(u'locations_governorate', 'area',
                      self.gf('django.contrib.gis.db.models.fields.PolygonField')(null=True, blank=True),
                      keep_default=False)

        # Deleting field 'Governorate.p_code'
        db.delete_column(u'locations_governorate', 'p_code')

        # Deleting field 'Governorate.gateway'
        db.delete_column(u'locations_governorate', 'gateway_id')

        # Deleting field 'Governorate.geom'
        db.delete_column(u'locations_governorate', 'geom')


    models = {
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'locations.cartodbtable': {
            'Meta': {'object_name': 'CartoDBTable'},
            'api_key': ('django.db.models.fields.CharField', [], {'max_length': '254'}),
            'domain': ('django.db.models.fields.CharField', [], {'max_length': '254'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'latitude_col': ('django.db.models.fields.CharField', [], {'default': "'latitude'", 'max_length': '254'}),
            'location_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['locations.GatewayType']"}),
            'longitude_col': ('django.db.models.fields.CharField', [], {'default': "'longitude'", 'max_length': '254'}),
            'name_col': ('django.db.models.fields.CharField', [], {'default': "'name'", 'max_length': '254'}),
            'parent_code_col': ('django.db.models.fields.CharField', [], {'max_length': '254', 'null': 'True', 'blank': 'True'}),
            'pcode_col': ('django.db.models.fields.CharField', [], {'default': "'pcode'", 'max_length': '254'}),
            'table_name': ('django.db.models.fields.CharField', [], {'max_length': '254'})
        },
        u'locations.gatewaytype': {
            'Meta': {'ordering': "['name']", 'object_name': 'GatewayType'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '64L'})
        },
        u'locations.governorate': {
            'Meta': {'ordering': "['name']", 'object_name': 'Governorate'},
            'gateway': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['locations.GatewayType']", 'null': 'True', 'blank': 'True'}),
            'geom': ('django.contrib.gis.db.models.fields.PolygonField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '45L'}),
            'p_code': ('django.db.models.fields.CharField', [], {'max_length': '32L', 'null': 'True', 'blank': 'True'})
        },
        u'locations.linkedlocation': {
            'Meta': {'object_name': 'LinkedLocation'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            'governorate': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['locations.Governorate']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'locality': ('smart_selects.db_fields.ChainedForeignKey', [], {'to': u"orm['locations.Locality']"}),
            'location': ('smart_selects.db_fields.ChainedForeignKey', [], {'to': u"orm['locations.Location']", 'null': 'True', 'blank': 'True'}),
            'object_id': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'region': ('smart_selects.db_fields.ChainedForeignKey', [], {'to': u"orm['locations.Region']"})
        },
        u'locations.locality': {
            'Meta': {'ordering': "['name']", 'unique_together': "(('name', 'cas_code_un'),)", 'object_name': 'Locality'},
            'cad_code': ('django.db.models.fields.CharField', [], {'max_length': '11L'}),
            'cas_code': ('django.db.models.fields.CharField', [], {'max_length': '11L'}),
            'cas_code_un': ('django.db.models.fields.CharField', [], {'max_length': '11L'}),
            'cas_village_name': ('django.db.models.fields.CharField', [], {'max_length': '128L'}),
            'gateway': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['locations.GatewayType']", 'null': 'True', 'blank': 'True'}),
            'geom': ('django.contrib.gis.db.models.fields.PolygonField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '128L'}),
            'p_code': ('django.db.models.fields.CharField', [], {'max_length': '32L', 'null': 'True', 'blank': 'True'}),
            'region': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['locations.Region']"})
        },
        u'locations.location': {
            'Meta': {'ordering': "['name']", 'unique_together': "(('name', 'gateway', 'p_code'),)", 'object_name': 'Location'},
            'gateway': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['locations.GatewayType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'latitude': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'locality': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['locations.Locality']"}),
            'longitude': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '254L'}),
            'p_code': ('django.db.models.fields.CharField', [], {'max_length': '32L', 'null': 'True', 'blank': 'True'}),
            'point': ('django.contrib.gis.db.models.fields.PointField', [], {})
        },
        u'locations.region': {
            'Meta': {'ordering': "['name']", 'object_name': 'Region'},
            'gateway': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['locations.GatewayType']", 'null': 'True', 'blank': 'True'}),
            'geom': ('django.contrib.gis.db.models.fields.PolygonField', [], {'null': 'True', 'blank': 'True'}),
            'governorate': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['locations.Governorate']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '45L'}),
            'p_code': ('django.db.models.fields.CharField', [], {'max_length': '32L', 'null': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['locations']