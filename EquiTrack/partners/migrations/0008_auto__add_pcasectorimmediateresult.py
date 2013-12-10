# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'PCASectorImmediateResult'
        db.create_table(u'partners_pcasectorimmediateresult', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('pca_sector', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['partners.PCASector'])),
            ('Intermediate_result', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['partners.IntermediateResult'])),
        ))
        db.send_create_signal(u'partners', ['PCASectorImmediateResult'])

        # Adding M2M table for field wbs_activities on 'PCASectorImmediateResult'
        m2m_table_name = db.shorten_name(u'partners_pcasectorimmediateresult_wbs_activities')
        db.create_table(m2m_table_name, (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('pcasectorimmediateresult', models.ForeignKey(orm[u'partners.pcasectorimmediateresult'], null=False)),
            ('wbs', models.ForeignKey(orm[u'partners.wbs'], null=False))
        ))
        db.create_unique(m2m_table_name, ['pcasectorimmediateresult_id', 'wbs_id'])

        # Removing M2M table for field wbs_activities on 'PCASector'
        db.delete_table(db.shorten_name(u'partners_pcasector_wbs_activities'))


    def backwards(self, orm):
        # Deleting model 'PCASectorImmediateResult'
        db.delete_table(u'partners_pcasectorimmediateresult')

        # Removing M2M table for field wbs_activities on 'PCASectorImmediateResult'
        db.delete_table(db.shorten_name(u'partners_pcasectorimmediateresult_wbs_activities'))

        # Adding M2M table for field wbs_activities on 'PCASector'
        m2m_table_name = db.shorten_name(u'partners_pcasector_wbs_activities')
        db.create_table(m2m_table_name, (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('pcasector', models.ForeignKey(orm[u'partners.pcasector'], null=False)),
            ('wbs', models.ForeignKey(orm[u'partners.wbs'], null=False))
        ))
        db.create_unique(m2m_table_name, ['pcasector_id', 'wbs_id'])


    models = {
        u'funds.donor': {
            'Meta': {'object_name': 'Donor'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '45L'})
        },
        u'funds.grant': {
            'Meta': {'object_name': 'Grant'},
            'donor': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['funds.Donor']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '128L'})
        },
        u'partners.goal': {
            'Meta': {'object_name': 'Goal'},
            'description': ('django.db.models.fields.CharField', [], {'max_length': '512L', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '512L'}),
            'sector': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['partners.Sector']"})
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
            'indicator': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['partners.Indicator']"}),
            'pca_sector': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['partners.PCASector']"}),
            'programmed': ('django.db.models.fields.IntegerField', [], {})
        },
        u'partners.intermediateresult': {
            'Meta': {'object_name': 'IntermediateResult'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'ir_wbs_reference': ('django.db.models.fields.CharField', [], {'max_length': '50L'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '128L'}),
            'sector': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['partners.Sector']"})
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
            'partner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['partners.PartnerOrganization']"}),
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
            'grant': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['funds.Grant']"}),
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
            'RRP5_outputs': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['partners.Rrp5Output']", 'symmetrical': 'False'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'pca': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['partners.PCA']"}),
            'sector': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['partners.Sector']"})
        },
        u'partners.pcasectorimmediateresult': {
            'Intermediate_result': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['partners.IntermediateResult']"}),
            'Meta': {'object_name': 'PCASectorImmediateResult'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'pca_sector': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['partners.PCASector']"}),
            'wbs_activities': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['partners.WBS']", 'symmetrical': 'False'})
        },
        u'partners.rrp5output': {
            'Meta': {'object_name': 'Rrp5Output'},
            'code': ('django.db.models.fields.CharField', [], {'max_length': '16L'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '256L'}),
            'sector': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['partners.Sector']"})
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
        },
        u'partners.wbs': {
            'Intermediate_result': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['partners.IntermediateResult']"}),
            'Meta': {'object_name': 'WBS'},
            'code': ('django.db.models.fields.CharField', [], {'max_length': '10L'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '128L'})
        }
    }

    complete_apps = ['partners']