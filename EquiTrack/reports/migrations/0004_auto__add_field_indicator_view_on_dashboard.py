# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Indicator.view_on_dashboard'
        db.add_column(u'reports_indicator', 'view_on_dashboard',
                      self.gf('django.db.models.fields.BooleanField')(default=False),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'Indicator.view_on_dashboard'
        db.delete_column(u'reports_indicator', 'view_on_dashboard')


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
            'ai_country_id': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True'}),
            'ai_id': ('django.db.models.fields.PositiveIntegerField', [], {}),
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
            'ai_id': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'category': ('django.db.models.fields.CharField', [], {'max_length': '254', 'null': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '254'}),
            'units': ('django.db.models.fields.CharField', [], {'max_length': '254'})
        },
        u'reports.activity': {
            'Meta': {'ordering': "['name']", 'object_name': 'Activity'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '128L'}),
            'sector': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['reports.Sector']"}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '30L', 'null': 'True', 'blank': 'True'})
        },
        u'reports.goal': {
            'Meta': {'ordering': "['name']", 'object_name': 'Goal'},
            'description': ('django.db.models.fields.CharField', [], {'max_length': '512L', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '512L'}),
            'result_structure': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['reports.ResultStructure']", 'null': 'True', 'blank': 'True'}),
            'sector': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'goals'", 'to': u"orm['reports.Sector']"})
        },
        u'reports.indicator': {
            'Meta': {'ordering': "['name']", 'object_name': 'Indicator'},
            'activity_info_indicators': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['activityinfo.Indicator']", 'symmetrical': 'False'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'in_activity_info': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '128L'}),
            'result_structure': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['reports.ResultStructure']", 'null': 'True', 'blank': 'True'}),
            'sector': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['reports.Sector']"}),
            'total': ('django.db.models.fields.IntegerField', [], {}),
            'unit': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['reports.Unit']"}),
            'view_on_dashboard': ('django.db.models.fields.BooleanField', [], {'default': 'False'})
        },
        u'reports.intermediateresult': {
            'Meta': {'ordering': "['name']", 'object_name': 'IntermediateResult'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'ir_wbs_reference': ('django.db.models.fields.CharField', [], {'max_length': '50L'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '128L'}),
            'sector': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['reports.Sector']"})
        },
        u'reports.resultstructure': {
            'Meta': {'ordering': "['name']", 'object_name': 'ResultStructure'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'})
        },
        u'reports.rrp5output': {
            'Meta': {'ordering': "['name']", 'unique_together': "(('result_structure', 'name'),)", 'object_name': 'Rrp5Output'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '256L'}),
            'objective': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['reports.RRPObjective']", 'null': 'True', 'blank': 'True'}),
            'result_structure': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['reports.ResultStructure']", 'null': 'True', 'blank': 'True'}),
            'sector': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['reports.Sector']"})
        },
        u'reports.rrpobjective': {
            'Meta': {'ordering': "['name']", 'object_name': 'RRPObjective'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '256L'}),
            'result_structure': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['reports.ResultStructure']", 'null': 'True', 'blank': 'True'}),
            'sector': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['reports.Sector']"})
        },
        u'reports.sector': {
            'Meta': {'ordering': "['name']", 'object_name': 'Sector'},
            'description': ('django.db.models.fields.CharField', [], {'max_length': '256L', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '45L'})
        },
        u'reports.unit': {
            'Meta': {'object_name': 'Unit'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'type': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '45L'})
        },
        u'reports.wbs': {
            'Intermediate_result': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['reports.IntermediateResult']"}),
            'Meta': {'ordering': "['name']", 'object_name': 'WBS'},
            'code': ('django.db.models.fields.CharField', [], {'max_length': '10L'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '128L'})
        }
    }

    complete_apps = ['reports']