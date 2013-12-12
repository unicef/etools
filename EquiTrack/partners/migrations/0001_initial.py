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
            ('partner', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['partners.PartnerOrganization'])),
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

        # Adding model 'PcaGrant'
        db.create_table(u'partners_pcagrant', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('pca', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['partners.PCA'])),
            ('grant', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['funds.Grant'])),
            ('funds', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
        ))
        db.send_create_signal(u'partners', ['PcaGrant'])

        # Adding model 'GwPcaLocation'
        db.create_table(u'partners_gwpcalocation', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('pca', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['partners.PCA'])),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=128L)),
            ('governorate', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['locations.Governorate'], null=True, blank=True)),
            ('region', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['locations.Region'], null=True, blank=True)),
            ('locality', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['locations.Locality'], null=True, blank=True)),
            ('gateway', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['locations.GatewayType'], null=True, blank=True)),
            ('location', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['locations.Location'])),
        ))
        db.send_create_signal(u'partners', ['GwPcaLocation'])

        # Adding model 'PCASector'
        db.create_table(u'partners_pcasector', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('pca', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['partners.PCA'])),
            ('sector', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['reports.Sector'])),
        ))
        db.send_create_signal(u'partners', ['PCASector'])

        # Adding M2M table for field RRP5_outputs on 'PCASector'
        m2m_table_name = db.shorten_name(u'partners_pcasector_RRP5_outputs')
        db.create_table(m2m_table_name, (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('pcasector', models.ForeignKey(orm[u'partners.pcasector'], null=False)),
            ('rrp5output', models.ForeignKey(orm[u'reports.rrp5output'], null=False))
        ))
        db.create_unique(m2m_table_name, ['pcasector_id', 'rrp5output_id'])

        # Adding M2M table for field activities on 'PCASector'
        m2m_table_name = db.shorten_name(u'partners_pcasector_activities')
        db.create_table(m2m_table_name, (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('pcasector', models.ForeignKey(orm[u'partners.pcasector'], null=False)),
            ('activity', models.ForeignKey(orm[u'reports.activity'], null=False))
        ))
        db.create_unique(m2m_table_name, ['pcasector_id', 'activity_id'])

        # Adding model 'PCASectorImmediateResult'
        db.create_table(u'partners_pcasectorimmediateresult', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('pca_sector', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['partners.PCASector'])),
            ('Intermediate_result', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['reports.IntermediateResult'])),
        ))
        db.send_create_signal(u'partners', ['PCASectorImmediateResult'])

        # Adding M2M table for field wbs_activities on 'PCASectorImmediateResult'
        m2m_table_name = db.shorten_name(u'partners_pcasectorimmediateresult_wbs_activities')
        db.create_table(m2m_table_name, (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('pcasectorimmediateresult', models.ForeignKey(orm[u'partners.pcasectorimmediateresult'], null=False)),
            ('wbs', models.ForeignKey(orm[u'reports.wbs'], null=False))
        ))
        db.create_unique(m2m_table_name, ['pcasectorimmediateresult_id', 'wbs_id'])

        # Adding model 'IndicatorProgress'
        db.create_table(u'partners_indicatorprogress', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('pca_sector', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['partners.PCASector'])),
            ('indicator', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['reports.Indicator'])),
            ('programmed', self.gf('django.db.models.fields.IntegerField')()),
            ('current', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
        ))
        db.send_create_signal(u'partners', ['IndicatorProgress'])

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

        # Deleting model 'PcaGrant'
        db.delete_table(u'partners_pcagrant')

        # Deleting model 'GwPcaLocation'
        db.delete_table(u'partners_gwpcalocation')

        # Deleting model 'PCASector'
        db.delete_table(u'partners_pcasector')

        # Removing M2M table for field RRP5_outputs on 'PCASector'
        db.delete_table(db.shorten_name(u'partners_pcasector_RRP5_outputs'))

        # Removing M2M table for field activities on 'PCASector'
        db.delete_table(db.shorten_name(u'partners_pcasector_activities'))

        # Deleting model 'PCASectorImmediateResult'
        db.delete_table(u'partners_pcasectorimmediateresult')

        # Removing M2M table for field wbs_activities on 'PCASectorImmediateResult'
        db.delete_table(db.shorten_name(u'partners_pcasectorimmediateresult_wbs_activities'))

        # Deleting model 'IndicatorProgress'
        db.delete_table(u'partners_indicatorprogress')

        # Deleting model 'PcaReport'
        db.delete_table(u'partners_pcareport')


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
        },
        u'partners.gwpcalocation': {
            'Meta': {'object_name': 'GwPcaLocation'},
            'gateway': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['locations.GatewayType']", 'null': 'True', 'blank': 'True'}),
            'governorate': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['locations.Governorate']", 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'locality': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['locations.Locality']", 'null': 'True', 'blank': 'True'}),
            'location': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['locations.Location']"}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '128L'}),
            'pca': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['partners.PCA']"}),
            'region': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['locations.Region']", 'null': 'True', 'blank': 'True'})
        },
        u'partners.indicatorprogress': {
            'Meta': {'object_name': 'IndicatorProgress'},
            'current': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'indicator': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['reports.Indicator']"}),
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
            'funds': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
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
            'RRP5_outputs': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['reports.Rrp5Output']", 'symmetrical': 'False'}),
            'activities': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['reports.Activity']", 'symmetrical': 'False'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'pca': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['partners.PCA']"}),
            'sector': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['reports.Sector']"})
        },
        u'partners.pcasectorimmediateresult': {
            'Intermediate_result': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['reports.IntermediateResult']"}),
            'Meta': {'object_name': 'PCASectorImmediateResult'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'pca_sector': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['partners.PCASector']"}),
            'wbs_activities': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['reports.WBS']", 'symmetrical': 'False'})
        },
        u'reports.activity': {
            'Meta': {'object_name': 'Activity'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '128L'}),
            'sector': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['reports.Sector']"}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '30L', 'null': 'True', 'blank': 'True'})
        },
        u'reports.goal': {
            'Meta': {'object_name': 'Goal'},
            'description': ('django.db.models.fields.CharField', [], {'max_length': '512L', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '512L'}),
            'sector': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['reports.Sector']"})
        },
        u'reports.indicator': {
            'Meta': {'object_name': 'Indicator'},
            'goal': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['reports.Goal']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '128L'}),
            'total': ('django.db.models.fields.IntegerField', [], {}),
            'unit': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['reports.Unit']"})
        },
        u'reports.intermediateresult': {
            'Meta': {'object_name': 'IntermediateResult'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'ir_wbs_reference': ('django.db.models.fields.CharField', [], {'max_length': '50L'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '128L'}),
            'sector': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['reports.Sector']"})
        },
        u'reports.rrp5output': {
            'Meta': {'object_name': 'Rrp5Output'},
            'code': ('django.db.models.fields.CharField', [], {'max_length': '16L'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '256L'}),
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
            'name': ('django.db.models.fields.CharField', [], {'max_length': '128L'})
        }
    }

    complete_apps = ['partners']