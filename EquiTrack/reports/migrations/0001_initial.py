# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'ResultStructure'
        db.create_table(u'reports_resultstructure', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=150)),
        ))
        db.send_create_signal(u'reports', ['ResultStructure'])

        # Adding model 'Sector'
        db.create_table(u'reports_sector', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(unique=True, max_length=45L)),
            ('description', self.gf('django.db.models.fields.CharField')(max_length=256L, null=True, blank=True)),
        ))
        db.send_create_signal(u'reports', ['Sector'])

        # Adding model 'RRPObjective'
        db.create_table(u'reports_rrpobjective', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('result_structure', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['reports.ResultStructure'], null=True, blank=True)),
            ('sector', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['reports.Sector'])),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=256L)),
        ))
        db.send_create_signal(u'reports', ['RRPObjective'])

        # Adding model 'Rrp5Output'
        db.create_table(u'reports_rrp5output', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('result_structure', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['reports.ResultStructure'], null=True, blank=True)),
            ('sector', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['reports.Sector'])),
            ('objective', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['reports.RRPObjective'], null=True, blank=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=256L)),
        ))
        db.send_create_signal(u'reports', ['Rrp5Output'])

        # Adding unique constraint on 'Rrp5Output', fields ['result_structure', 'name']
        db.create_unique(u'reports_rrp5output', ['result_structure_id', 'name'])

        # Adding model 'Goal'
        db.create_table(u'reports_goal', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('result_structure', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['reports.ResultStructure'], null=True, blank=True)),
            ('sector', self.gf('django.db.models.fields.related.ForeignKey')(related_name='goals', to=orm['reports.Sector'])),
            ('name', self.gf('django.db.models.fields.CharField')(unique=True, max_length=512L)),
            ('description', self.gf('django.db.models.fields.CharField')(max_length=512L, blank=True)),
        ))
        db.send_create_signal(u'reports', ['Goal'])

        # Adding model 'Unit'
        db.create_table(u'reports_unit', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('type', self.gf('django.db.models.fields.CharField')(unique=True, max_length=45L)),
        ))
        db.send_create_signal(u'reports', ['Unit'])

        # Adding model 'Indicator'
        db.create_table(u'reports_indicator', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('sector', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['reports.Sector'])),
            ('result_structure', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['reports.ResultStructure'], null=True, blank=True)),
            ('name', self.gf('django.db.models.fields.CharField')(unique=True, max_length=128L)),
            ('unit', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['reports.Unit'])),
            ('total', self.gf('django.db.models.fields.IntegerField')()),
        ))
        db.send_create_signal(u'reports', ['Indicator'])

        # Adding model 'IntermediateResult'
        db.create_table(u'reports_intermediateresult', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('sector', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['reports.Sector'])),
            ('ir_wbs_reference', self.gf('django.db.models.fields.CharField')(max_length=50L)),
            ('name', self.gf('django.db.models.fields.CharField')(unique=True, max_length=128L)),
        ))
        db.send_create_signal(u'reports', ['IntermediateResult'])

        # Adding model 'WBS'
        db.create_table(u'reports_wbs', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('Intermediate_result', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['reports.IntermediateResult'])),
            ('name', self.gf('django.db.models.fields.CharField')(unique=True, max_length=128L)),
            ('code', self.gf('django.db.models.fields.CharField')(max_length=10L)),
        ))
        db.send_create_signal(u'reports', ['WBS'])

        # Adding model 'Activity'
        db.create_table(u'reports_activity', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('sector', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['reports.Sector'])),
            ('name', self.gf('django.db.models.fields.CharField')(unique=True, max_length=128L)),
            ('type', self.gf('django.db.models.fields.CharField')(max_length=30L, null=True, blank=True)),
        ))
        db.send_create_signal(u'reports', ['Activity'])


    def backwards(self, orm):
        # Removing unique constraint on 'Rrp5Output', fields ['result_structure', 'name']
        db.delete_unique(u'reports_rrp5output', ['result_structure_id', 'name'])

        # Deleting model 'ResultStructure'
        db.delete_table(u'reports_resultstructure')

        # Deleting model 'Sector'
        db.delete_table(u'reports_sector')

        # Deleting model 'RRPObjective'
        db.delete_table(u'reports_rrpobjective')

        # Deleting model 'Rrp5Output'
        db.delete_table(u'reports_rrp5output')

        # Deleting model 'Goal'
        db.delete_table(u'reports_goal')

        # Deleting model 'Unit'
        db.delete_table(u'reports_unit')

        # Deleting model 'Indicator'
        db.delete_table(u'reports_indicator')

        # Deleting model 'IntermediateResult'
        db.delete_table(u'reports_intermediateresult')

        # Deleting model 'WBS'
        db.delete_table(u'reports_wbs')

        # Deleting model 'Activity'
        db.delete_table(u'reports_activity')


    models = {
        u'reports.activity': {
            'Meta': {'object_name': 'Activity'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '128L'}),
            'sector': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['reports.Sector']"}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '30L', 'null': 'True', 'blank': 'True'})
        },
        u'reports.goal': {
            'Meta': {'object_name': 'Goal'},
            'description': ('django.db.models.fields.CharField', [], {'max_length': '512L', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '512L'}),
            'result_structure': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['reports.ResultStructure']", 'null': 'True', 'blank': 'True'}),
            'sector': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'goals'", 'to': u"orm['reports.Sector']"})
        },
        u'reports.indicator': {
            'Meta': {'object_name': 'Indicator'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '128L'}),
            'result_structure': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['reports.ResultStructure']", 'null': 'True', 'blank': 'True'}),
            'sector': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['reports.Sector']"}),
            'total': ('django.db.models.fields.IntegerField', [], {}),
            'unit': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['reports.Unit']"})
        },
        u'reports.intermediateresult': {
            'Meta': {'object_name': 'IntermediateResult'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'ir_wbs_reference': ('django.db.models.fields.CharField', [], {'max_length': '50L'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '128L'}),
            'sector': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['reports.Sector']"})
        },
        u'reports.resultstructure': {
            'Meta': {'object_name': 'ResultStructure'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'})
        },
        u'reports.rrp5output': {
            'Meta': {'unique_together': "(('result_structure', 'name'),)", 'object_name': 'Rrp5Output'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '256L'}),
            'objective': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['reports.RRPObjective']", 'null': 'True', 'blank': 'True'}),
            'result_structure': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['reports.ResultStructure']", 'null': 'True', 'blank': 'True'}),
            'sector': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['reports.Sector']"})
        },
        u'reports.rrpobjective': {
            'Meta': {'object_name': 'RRPObjective'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '256L'}),
            'result_structure': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['reports.ResultStructure']", 'null': 'True', 'blank': 'True'}),
            'sector': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['reports.Sector']"})
        },
        u'reports.sector': {
            'Meta': {'object_name': 'Sector'},
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
            'Meta': {'object_name': 'WBS'},
            'code': ('django.db.models.fields.CharField', [], {'max_length': '10L'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '128L'})
        }
    }

    complete_apps = ['reports']