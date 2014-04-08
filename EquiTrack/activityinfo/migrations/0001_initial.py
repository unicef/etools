# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Database'
        db.create_table(u'activityinfo_database', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('ai_id', self.gf('django.db.models.fields.PositiveIntegerField')()),
            ('username', self.gf('django.db.models.fields.CharField')(max_length=254)),
            ('passowrd', self.gf('django.db.models.fields.CharField')(max_length=254)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=254)),
            ('description', self.gf('django.db.models.fields.CharField')(max_length=254)),
            ('country_name', self.gf('django.db.models.fields.CharField')(max_length=254)),
            ('ai_country_id', self.gf('django.db.models.fields.PositiveIntegerField')()),
        ))
        db.send_create_signal(u'activityinfo', ['Database'])

        # Adding model 'Partner'
        db.create_table(u'activityinfo_partner', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('ai_id', self.gf('django.db.models.fields.PositiveIntegerField')()),
            ('database', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['activityinfo.Database'])),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=254)),
            ('full_name', self.gf('django.db.models.fields.CharField')(max_length=254)),
        ))
        db.send_create_signal(u'activityinfo', ['Partner'])

        # Adding model 'Activity'
        db.create_table(u'activityinfo_activity', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('ai_id', self.gf('django.db.models.fields.PositiveIntegerField')()),
            ('database', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['activityinfo.Database'])),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=254)),
            ('location_type', self.gf('django.db.models.fields.CharField')(max_length=254)),
        ))
        db.send_create_signal(u'activityinfo', ['Activity'])

        # Adding model 'Indicator'
        db.create_table(u'activityinfo_indicator', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('ai_id', self.gf('django.db.models.fields.PositiveIntegerField')()),
            ('activity', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['activityinfo.Activity'])),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=254)),
            ('description', self.gf('django.db.models.fields.CharField')(max_length=254)),
            ('units', self.gf('django.db.models.fields.CharField')(max_length=254)),
            ('category', self.gf('django.db.models.fields.CharField')(max_length=254)),
        ))
        db.send_create_signal(u'activityinfo', ['Indicator'])


    def backwards(self, orm):
        # Deleting model 'Database'
        db.delete_table(u'activityinfo_database')

        # Deleting model 'Partner'
        db.delete_table(u'activityinfo_partner')

        # Deleting model 'Activity'
        db.delete_table(u'activityinfo_activity')

        # Deleting model 'Indicator'
        db.delete_table(u'activityinfo_indicator')


    models = {
        u'activityinfo.activity': {
            'Meta': {'object_name': 'Activity'},
            'ai_id': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'database': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['activityinfo.Database']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'location_type': ('django.db.models.fields.CharField', [], {'max_length': '254'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '254'})
        },
        u'activityinfo.database': {
            'Meta': {'object_name': 'Database'},
            'ai_country_id': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'ai_id': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'country_name': ('django.db.models.fields.CharField', [], {'max_length': '254'}),
            'description': ('django.db.models.fields.CharField', [], {'max_length': '254'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '254'}),
            'passowrd': ('django.db.models.fields.CharField', [], {'max_length': '254'}),
            'username': ('django.db.models.fields.CharField', [], {'max_length': '254'})
        },
        u'activityinfo.indicator': {
            'Meta': {'object_name': 'Indicator'},
            'activity': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['activityinfo.Activity']"}),
            'ai_id': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'category': ('django.db.models.fields.CharField', [], {'max_length': '254'}),
            'description': ('django.db.models.fields.CharField', [], {'max_length': '254'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '254'}),
            'units': ('django.db.models.fields.CharField', [], {'max_length': '254'})
        },
        u'activityinfo.partner': {
            'Meta': {'object_name': 'Partner'},
            'ai_id': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'database': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['activityinfo.Database']"}),
            'full_name': ('django.db.models.fields.CharField', [], {'max_length': '254'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '254'})
        }
    }

    complete_apps = ['activityinfo']