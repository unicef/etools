# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Database'
        db.create_table(u'activityinfo_database', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('ai_id', self.gf('django.db.models.fields.PositiveIntegerField')(unique=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=254)),
            ('username', self.gf('django.db.models.fields.CharField')(max_length=254)),
            ('password', self.gf('django.db.models.fields.CharField')(max_length=254)),
            ('description', self.gf('django.db.models.fields.CharField')(max_length=254, null=True)),
            ('country_name', self.gf('django.db.models.fields.CharField')(max_length=254, null=True)),
            ('ai_country_id', self.gf('django.db.models.fields.PositiveIntegerField')(null=True)),
        ))
        db.send_create_signal(u'activityinfo', ['Database'])

        # Adding model 'Partner'
        db.create_table(u'activityinfo_partner', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('ai_id', self.gf('django.db.models.fields.PositiveIntegerField')(unique=True)),
            ('database', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['activityinfo.Database'])),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=254)),
            ('full_name', self.gf('django.db.models.fields.CharField')(max_length=254, null=True)),
        ))
        db.send_create_signal(u'activityinfo', ['Partner'])

        # Adding model 'Activity'
        db.create_table(u'activityinfo_activity', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('ai_id', self.gf('django.db.models.fields.PositiveIntegerField')(unique=True)),
            ('database', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['activityinfo.Database'])),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=254)),
            ('location_type', self.gf('django.db.models.fields.CharField')(max_length=254)),
        ))
        db.send_create_signal(u'activityinfo', ['Activity'])

        # Adding model 'Indicator'
        db.create_table(u'activityinfo_indicator', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('ai_id', self.gf('django.db.models.fields.PositiveIntegerField')(unique=True)),
            ('activity', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['activityinfo.Activity'])),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=254)),
            ('units', self.gf('django.db.models.fields.CharField')(max_length=254)),
            ('category', self.gf('django.db.models.fields.CharField')(max_length=254, null=True)),
        ))
        db.send_create_signal(u'activityinfo', ['Indicator'])

        # Adding model 'AttributeGroup'
        db.create_table(u'activityinfo_attributegroup', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('activity', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['activityinfo.Activity'])),
            ('ai_id', self.gf('django.db.models.fields.PositiveIntegerField')(unique=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=254)),
            ('multiple_allowed', self.gf('django.db.models.fields.BooleanField')()),
            ('mandatory', self.gf('django.db.models.fields.BooleanField')()),
        ))
        db.send_create_signal(u'activityinfo', ['AttributeGroup'])

        # Adding model 'Attribute'
        db.create_table(u'activityinfo_attribute', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('attribute_group', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['activityinfo.AttributeGroup'])),
            ('ai_id', self.gf('django.db.models.fields.PositiveIntegerField')(unique=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=254)),
        ))
        db.send_create_signal(u'activityinfo', ['Attribute'])


    def backwards(self, orm):
        # Deleting model 'Database'
        db.delete_table(u'activityinfo_database')

        # Deleting model 'Partner'
        db.delete_table(u'activityinfo_partner')

        # Deleting model 'Activity'
        db.delete_table(u'activityinfo_activity')

        # Deleting model 'Indicator'
        db.delete_table(u'activityinfo_indicator')

        # Deleting model 'AttributeGroup'
        db.delete_table(u'activityinfo_attributegroup')

        # Deleting model 'Attribute'
        db.delete_table(u'activityinfo_attribute')


    models = {
        u'activityinfo.activity': {
            'Meta': {'object_name': 'Activity'},
            'ai_id': ('django.db.models.fields.PositiveIntegerField', [], {'unique': 'True'}),
            'database': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['activityinfo.Database']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'location_type': ('django.db.models.fields.CharField', [], {'max_length': '254'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '254'})
        },
        u'activityinfo.attribute': {
            'Meta': {'object_name': 'Attribute'},
            'ai_id': ('django.db.models.fields.PositiveIntegerField', [], {'unique': 'True'}),
            'attribute_group': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['activityinfo.AttributeGroup']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '254'})
        },
        u'activityinfo.attributegroup': {
            'Meta': {'object_name': 'AttributeGroup'},
            'activity': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['activityinfo.Activity']"}),
            'ai_id': ('django.db.models.fields.PositiveIntegerField', [], {'unique': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'mandatory': ('django.db.models.fields.BooleanField', [], {}),
            'multiple_allowed': ('django.db.models.fields.BooleanField', [], {}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '254'})
        },
        u'activityinfo.database': {
            'Meta': {'object_name': 'Database'},
            'ai_country_id': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True'}),
            'ai_id': ('django.db.models.fields.PositiveIntegerField', [], {'unique': 'True'}),
            'country_name': ('django.db.models.fields.CharField', [], {'max_length': '254', 'null': 'True'}),
            'description': ('django.db.models.fields.CharField', [], {'max_length': '254', 'null': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '254'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '254'}),
            'username': ('django.db.models.fields.CharField', [], {'max_length': '254'})
        },
        u'activityinfo.indicator': {
            'Meta': {'object_name': 'Indicator'},
            'activity': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['activityinfo.Activity']"}),
            'ai_id': ('django.db.models.fields.PositiveIntegerField', [], {'unique': 'True'}),
            'category': ('django.db.models.fields.CharField', [], {'max_length': '254', 'null': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '254'}),
            'units': ('django.db.models.fields.CharField', [], {'max_length': '254'})
        },
        u'activityinfo.partner': {
            'Meta': {'ordering': "['name']", 'object_name': 'Partner'},
            'ai_id': ('django.db.models.fields.PositiveIntegerField', [], {'unique': 'True'}),
            'database': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['activityinfo.Database']"}),
            'full_name': ('django.db.models.fields.CharField', [], {'max_length': '254', 'null': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '254'})
        }
    }

    complete_apps = ['activityinfo']