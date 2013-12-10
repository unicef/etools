# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Deleting field 'Location.governorate'
        db.delete_column(u'locations_location', 'governorate_id')

        # Deleting field 'Location.locality'
        db.delete_column(u'locations_location', 'locality_id')

        # Deleting field 'Location.region'
        db.delete_column(u'locations_location', 'region_id')

        # Deleting field 'Location.gateway_type'
        db.delete_column(u'locations_location', 'gateway_type_id')

        # Deleting field 'Location.pca'
        db.delete_column(u'locations_location', 'pca_id')


    def backwards(self, orm):
        # Adding field 'Location.governorate'
        db.add_column(u'locations_location', 'governorate',
                      self.gf('django.db.models.fields.related.ForeignKey')(to=orm['locations.Governorate'], null=True, blank=True),
                      keep_default=False)

        # Adding field 'Location.locality'
        db.add_column(u'locations_location', 'locality',
                      self.gf('django.db.models.fields.related.ForeignKey')(to=orm['locations.Locality'], null=True, blank=True),
                      keep_default=False)

        # Adding field 'Location.region'
        db.add_column(u'locations_location', 'region',
                      self.gf('django.db.models.fields.related.ForeignKey')(to=orm['locations.Region'], null=True, blank=True),
                      keep_default=False)

        # Adding field 'Location.gateway_type'
        db.add_column(u'locations_location', 'gateway_type',
                      self.gf('django.db.models.fields.related.ForeignKey')(default=0, to=orm['locations.GatewayType']),
                      keep_default=False)

        # Adding field 'Location.pca'
        db.add_column(u'locations_location', 'pca',
                      self.gf('django.db.models.fields.related.ForeignKey')(default=0, to=orm['partners.PCA']),
                      keep_default=False)


    models = {
        u'locations.gatewaytype': {
            'Meta': {'object_name': 'GatewayType'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '64L'})
        },
        u'locations.governorate': {
            'Meta': {'object_name': 'Governorate'},
            'area': ('django.contrib.gis.db.models.fields.MultiPointField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '45L'})
        },
        u'locations.locality': {
            'Meta': {'object_name': 'Locality'},
            'area': ('django.contrib.gis.db.models.fields.MultiPointField', [], {'null': 'True', 'blank': 'True'}),
            'cad_code': ('django.db.models.fields.CharField', [], {'max_length': '11L'}),
            'cas_code': ('django.db.models.fields.CharField', [], {'max_length': '11L'}),
            'cas_code_un': ('django.db.models.fields.CharField', [], {'max_length': '11L'}),
            'cas_village_name': ('django.db.models.fields.CharField', [], {'max_length': '128L'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '128L'}),
            'region': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['locations.Region']"})
        },
        u'locations.location': {
            'Meta': {'object_name': 'Location'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'latitude': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'longitude': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '45L', 'blank': 'True'}),
            'p_code': ('django.db.models.fields.CharField', [], {'max_length': '32L', 'blank': 'True'}),
            'point': ('django.contrib.gis.db.models.fields.PointField', [], {'null': 'True', 'blank': 'True'})
        },
        u'locations.region': {
            'Meta': {'object_name': 'Region'},
            'area': ('django.contrib.gis.db.models.fields.MultiPointField', [], {'null': 'True', 'blank': 'True'}),
            'governorate': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['locations.Governorate']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '45L'})
        }
    }

    complete_apps = ['locations']