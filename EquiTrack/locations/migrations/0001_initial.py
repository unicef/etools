# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Governorate'
        db.create_table(u'locations_governorate', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=45L)),
            ('area', self.gf('django.contrib.gis.db.models.fields.MultiPointField')(null=True, blank=True)),
        ))
        db.send_create_signal(u'locations', ['Governorate'])

        # Adding model 'Region'
        db.create_table(u'locations_region', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('governorate', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['locations.Governorate'])),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=45L)),
            ('area', self.gf('django.contrib.gis.db.models.fields.MultiPointField')(null=True, blank=True)),
        ))
        db.send_create_signal(u'locations', ['Region'])

        # Adding model 'Locality'
        db.create_table(u'locations_locality', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('region', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['locations.Region'])),
            ('cad_code', self.gf('django.db.models.fields.CharField')(max_length=11L)),
            ('cas_code', self.gf('django.db.models.fields.CharField')(max_length=11L)),
            ('cas_code_un', self.gf('django.db.models.fields.CharField')(max_length=11L)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=128L)),
            ('cas_village_name', self.gf('django.db.models.fields.CharField')(max_length=128L)),
            ('area', self.gf('django.contrib.gis.db.models.fields.MultiPointField')(null=True, blank=True)),
        ))
        db.send_create_signal(u'locations', ['Locality'])

        # Adding model 'GatewayType'
        db.create_table(u'locations_gatewaytype', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=64L)),
        ))
        db.send_create_signal(u'locations', ['GatewayType'])

        # Adding model 'Location'
        db.create_table(u'locations_location', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=45L, blank=True)),
            ('locality', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['locations.Locality'], null=True, blank=True)),
            ('latitude', self.gf('django.db.models.fields.FloatField')(null=True, blank=True)),
            ('longitude', self.gf('django.db.models.fields.FloatField')(null=True, blank=True)),
            ('p_code', self.gf('django.db.models.fields.CharField')(max_length=32L, blank=True)),
            ('point', self.gf('django.contrib.gis.db.models.fields.PointField')(null=True, blank=True)),
        ))
        db.send_create_signal(u'locations', ['Location'])


    def backwards(self, orm):
        # Deleting model 'Governorate'
        db.delete_table(u'locations_governorate')

        # Deleting model 'Region'
        db.delete_table(u'locations_region')

        # Deleting model 'Locality'
        db.delete_table(u'locations_locality')

        # Deleting model 'GatewayType'
        db.delete_table(u'locations_gatewaytype')

        # Deleting model 'Location'
        db.delete_table(u'locations_location')


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
            'locality': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['locations.Locality']", 'null': 'True', 'blank': 'True'}),
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