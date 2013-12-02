# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'IndicatorProgress'
        db.create_table(u'partners_indicatorprogress', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('pca_sector', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['partners.PCASector'])),
            ('programmed', self.gf('django.db.models.fields.IntegerField')()),
            ('current', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
        ))
        db.send_create_signal(u'partners', ['IndicatorProgress'])

        # Deleting field 'Indicator.current'
        db.delete_column(u'partners_indicator', 'current')

        # Deleting field 'Indicator.pca_sector'
        db.delete_column(u'partners_indicator', 'pca_sector_id')

        # Deleting field 'Indicator.programmed'
        db.delete_column(u'partners_indicator', 'programmed')


    def backwards(self, orm):
        # Deleting model 'IndicatorProgress'
        db.delete_table(u'partners_indicatorprogress')

        # Adding field 'Indicator.current'
        db.add_column(u'partners_indicator', 'current',
                      self.gf('django.db.models.fields.IntegerField')(default=1),
                      keep_default=False)

        # Adding field 'Indicator.pca_sector'
        db.add_column(u'partners_indicator', 'pca_sector',
                      self.gf('django.db.models.fields.related.ForeignKey')(default=1, to=orm['partners.PCASector']),
                      keep_default=False)

        # Adding field 'Indicator.programmed'
        db.add_column(u'partners_indicator', 'programmed',
                      self.gf('django.db.models.fields.IntegerField')(default=1),
                      keep_default=False)


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
            'goal': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['partners.Goal']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '128L'}),
            'unit': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['partners.Unit']"})
        },
        u'partners.indicatorprogress': {
            'Meta': {'object_name': 'IndicatorProgress'},
            'current': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'pca_sector': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['partners.PCASector']"}),
            'programmed': ('django.db.models.fields.IntegerField', [], {})
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