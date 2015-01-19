# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Deleting model 'PartnerReport'
        db.delete_table(u'activityinfo_partnerreport')


    def backwards(self, orm):
        # Adding model 'PartnerReport'
        db.create_table(u'activityinfo_partnerreport', (
            ('indicator', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['reports.Indicator'])),
            ('ai_indicator', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['activityinfo.Indicator'])),
            ('location', self.gf('django.db.models.fields.CharField')(max_length=254)),
            ('ai_partner', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['activityinfo.Partner'])),
            ('created_at', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, null=True, blank=True)),
            ('pca', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['partners.PCA'])),
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('indicator_value', self.gf('django.db.models.fields.IntegerField')()),
            ('month', self.gf('django.db.models.fields.DateField')()),
        ))
        db.send_create_signal(u'activityinfo', ['PartnerReport'])


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