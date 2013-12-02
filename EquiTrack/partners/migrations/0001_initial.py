# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'PartnerOrganization'
        db.create_table(u'partners_partnerorganization', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=45L)),
            ('description', self.gf('django.db.models.fields.CharField')(max_length=256L, blank=True)),
            ('email', self.gf('django.db.models.fields.CharField')(max_length=128L, blank=True)),
            ('contact_person', self.gf('django.db.models.fields.CharField')(max_length=64L, blank=True)),
            ('phone_number', self.gf('django.db.models.fields.CharField')(max_length=32L, blank=True)),
        ))
        db.send_create_signal(u'partners', ['PartnerOrganization'])

        # Adding model 'PCA'
        db.create_table(u'partners_pca', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('number', self.gf('django.db.models.fields.CharField')(max_length=45L, blank=True)),
            ('title', self.gf('django.db.models.fields.CharField')(max_length=256L, blank=True)),
            ('status', self.gf('django.db.models.fields.CharField')(max_length=32L, blank=True)),
            ('partner', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['partners.PartnerOrganization'], null=True, blank=True)),
            ('start_date', self.gf('django.db.models.fields.DateField')(null=True, blank=True)),
            ('end_date', self.gf('django.db.models.fields.DateField')(null=True, blank=True)),
            ('initiation_date', self.gf('django.db.models.fields.DateField')(null=True, blank=True)),
            ('signed_by_unicef_date', self.gf('django.db.models.fields.DateField')(null=True, blank=True)),
            ('signed_by_partner_date', self.gf('django.db.models.fields.DateField')(null=True, blank=True)),
            ('unicef_mng_first_name', self.gf('django.db.models.fields.CharField')(max_length=64L, blank=True)),
            ('unicef_mng_last_name', self.gf('django.db.models.fields.CharField')(max_length=64L, blank=True)),
            ('unicef_mng_email', self.gf('django.db.models.fields.CharField')(max_length=128L, blank=True)),
            ('partner_mng_first_name', self.gf('django.db.models.fields.CharField')(max_length=64L, blank=True)),
            ('partner_mng_last_name', self.gf('django.db.models.fields.CharField')(max_length=64L, blank=True)),
            ('partner_mng_email', self.gf('django.db.models.fields.CharField')(max_length=128L, blank=True)),
            ('partner_contribution_budget', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('unicef_cash_budget', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('in_kind_amount_budget', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('cash_for_supply_budget', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('total_cash', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('received_date', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('is_approved', self.gf('django.db.models.fields.NullBooleanField')(null=True, blank=True)),
        ))
        db.send_create_signal(u'partners', ['PCA'])

        # Adding model 'Donor'
        db.create_table(u'partners_donor', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=45L, blank=True)),
        ))
        db.send_create_signal(u'partners', ['Donor'])

        # Adding model 'Grant'
        db.create_table(u'partners_grant', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('donor', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['partners.Donor'])),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=128L)),
        ))
        db.send_create_signal(u'partners', ['Grant'])

        # Adding model 'PcaGrant'
        db.create_table(u'partners_pcagrant', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('pca', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['partners.PCA'])),
            ('grant', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['partners.Grant'])),
            ('funds', self.gf('django.db.models.fields.IntegerField')()),
        ))
        db.send_create_signal(u'partners', ['PcaGrant'])

        # Adding model 'Sector'
        db.create_table(u'partners_sector', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=45L)),
            ('description', self.gf('django.db.models.fields.CharField')(max_length=256L, blank=True)),
        ))
        db.send_create_signal(u'partners', ['Sector'])

        # Adding model 'PCASector'
        db.create_table(u'partners_pcasector', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('pca', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['partners.PCA'])),
            ('sector', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['partners.Sector'])),
        ))
        db.send_create_signal(u'partners', ['PCASector'])

        # Adding model 'Rrp5Output'
        db.create_table(u'partners_rrp5output', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('pca_sector', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['partners.PCASector'])),
            ('code', self.gf('django.db.models.fields.CharField')(max_length=16L)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=256L)),
        ))
        db.send_create_signal(u'partners', ['Rrp5Output'])

        # Adding model 'Goal'
        db.create_table(u'partners_goal', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('sector', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['partners.Sector'])),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=512L)),
            ('description', self.gf('django.db.models.fields.CharField')(max_length=512L, blank=True)),
        ))
        db.send_create_signal(u'partners', ['Goal'])

        # Adding model 'Unit'
        db.create_table(u'partners_unit', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('type', self.gf('django.db.models.fields.CharField')(max_length=45L)),
        ))
        db.send_create_signal(u'partners', ['Unit'])

        # Adding model 'Indicator'
        db.create_table(u'partners_indicator', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('pca_sector', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['partners.PCASector'])),
            ('goal', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['partners.Goal'])),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=128L)),
            ('unit', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['partners.Unit'])),
            ('programmed', self.gf('django.db.models.fields.IntegerField')()),
            ('current', self.gf('django.db.models.fields.IntegerField')()),
        ))
        db.send_create_signal(u'partners', ['Indicator'])

        # Adding model 'PcaReport'
        db.create_table(u'partners_pcareport', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('pca', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['partners.PCA'])),
            ('title', self.gf('django.db.models.fields.CharField')(max_length=128L)),
            ('description', self.gf('django.db.models.fields.CharField')(max_length=512L)),
            ('start_period', self.gf('django.db.models.fields.DateField')(null=True, blank=True)),
            ('end_period', self.gf('django.db.models.fields.DateField')(null=True, blank=True)),
            ('received_date', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
        ))
        db.send_create_signal(u'partners', ['PcaReport'])


    def backwards(self, orm):
        # Deleting model 'PartnerOrganization'
        db.delete_table(u'partners_partnerorganization')

        # Deleting model 'PCA'
        db.delete_table(u'partners_pca')

        # Deleting model 'Donor'
        db.delete_table(u'partners_donor')

        # Deleting model 'Grant'
        db.delete_table(u'partners_grant')

        # Deleting model 'PcaGrant'
        db.delete_table(u'partners_pcagrant')

        # Deleting model 'Sector'
        db.delete_table(u'partners_sector')

        # Deleting model 'PCASector'
        db.delete_table(u'partners_pcasector')

        # Deleting model 'Rrp5Output'
        db.delete_table(u'partners_rrp5output')

        # Deleting model 'Goal'
        db.delete_table(u'partners_goal')

        # Deleting model 'Unit'
        db.delete_table(u'partners_unit')

        # Deleting model 'Indicator'
        db.delete_table(u'partners_indicator')

        # Deleting model 'PcaReport'
        db.delete_table(u'partners_pcareport')


    models = {
        u'partners.donor': {
            'Meta': {'object_name': 'Donor'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '45L', 'blank': 'True'})
        },
        u'partners.goal': {
            'Meta': {'object_name': 'Goal'},
            'description': ('django.db.models.fields.CharField', [], {'max_length': '512L', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '512L'}),
            'sector': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['partners.Sector']"})
        },
        u'partners.grant': {
            'Meta': {'object_name': 'Grant'},
            'donor': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['partners.Donor']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '128L'})
        },
        u'partners.indicator': {
            'Meta': {'object_name': 'Indicator'},
            'current': ('django.db.models.fields.IntegerField', [], {}),
            'goal': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['partners.Goal']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '128L'}),
            'pca_sector': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['partners.PCASector']"}),
            'programmed': ('django.db.models.fields.IntegerField', [], {}),
            'unit': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['partners.Unit']"})
        },
        u'partners.partnerorganization': {
            'Meta': {'object_name': 'PartnerOrganization'},
            'contact_person': ('django.db.models.fields.CharField', [], {'max_length': '64L', 'blank': 'True'}),
            'description': ('django.db.models.fields.CharField', [], {'max_length': '256L', 'blank': 'True'}),
            'email': ('django.db.models.fields.CharField', [], {'max_length': '128L', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '45L'}),
            'phone_number': ('django.db.models.fields.CharField', [], {'max_length': '32L', 'blank': 'True'})
        },
        u'partners.pca': {
            'Meta': {'object_name': 'PCA'},
            'cash_for_supply_budget': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'end_date': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'in_kind_amount_budget': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'initiation_date': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'is_approved': ('django.db.models.fields.NullBooleanField', [], {'null': 'True', 'blank': 'True'}),
            'number': ('django.db.models.fields.CharField', [], {'max_length': '45L', 'blank': 'True'}),
            'partner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['partners.PartnerOrganization']", 'null': 'True', 'blank': 'True'}),
            'partner_contribution_budget': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'partner_mng_email': ('django.db.models.fields.CharField', [], {'max_length': '128L', 'blank': 'True'}),
            'partner_mng_first_name': ('django.db.models.fields.CharField', [], {'max_length': '64L', 'blank': 'True'}),
            'partner_mng_last_name': ('django.db.models.fields.CharField', [], {'max_length': '64L', 'blank': 'True'}),
            'received_date': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'signed_by_partner_date': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'signed_by_unicef_date': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'start_date': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'status': ('django.db.models.fields.CharField', [], {'max_length': '32L', 'blank': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '256L', 'blank': 'True'}),
            'total_cash': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'unicef_cash_budget': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'unicef_mng_email': ('django.db.models.fields.CharField', [], {'max_length': '128L', 'blank': 'True'}),
            'unicef_mng_first_name': ('django.db.models.fields.CharField', [], {'max_length': '64L', 'blank': 'True'}),
            'unicef_mng_last_name': ('django.db.models.fields.CharField', [], {'max_length': '64L', 'blank': 'True'})
        },
        u'partners.pcagrant': {
            'Meta': {'object_name': 'PcaGrant'},
            'funds': ('django.db.models.fields.IntegerField', [], {}),
            'grant': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['partners.Grant']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'pca': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['partners.PCA']"})
        },
        u'partners.pcareport': {
            'Meta': {'object_name': 'PcaReport'},
            'description': ('django.db.models.fields.CharField', [], {'max_length': '512L'}),
            'end_period': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'pca': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['partners.PCA']"}),
            'received_date': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'start_period': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '128L'})
        },
        u'partners.pcasector': {
            'Meta': {'object_name': 'PCASector'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'pca': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['partners.PCA']"}),
            'sector': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['partners.Sector']"})
        },
        u'partners.rrp5output': {
            'Meta': {'object_name': 'Rrp5Output'},
            'code': ('django.db.models.fields.CharField', [], {'max_length': '16L'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '256L'}),
            'pca_sector': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['partners.PCASector']"})
        },
        u'partners.sector': {
            'Meta': {'object_name': 'Sector'},
            'description': ('django.db.models.fields.CharField', [], {'max_length': '256L', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '45L'})
        },
        u'partners.unit': {
            'Meta': {'object_name': 'Unit'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '45L'})
        }
    }

    complete_apps = ['partners']