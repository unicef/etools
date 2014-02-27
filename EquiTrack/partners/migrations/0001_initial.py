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
            ('name', self.gf('django.db.models.fields.CharField')(unique=True, max_length=45L)),
            ('description', self.gf('django.db.models.fields.CharField')(max_length=256L, blank=True)),
            ('email', self.gf('django.db.models.fields.CharField')(max_length=128L, blank=True)),
            ('contact_person', self.gf('django.db.models.fields.CharField')(max_length=64L, blank=True)),
            ('phone_number', self.gf('django.db.models.fields.CharField')(max_length=32L, blank=True)),
        ))
        db.send_create_signal(u'partners', ['PartnerOrganization'])

        # Adding model 'PCA'
        db.create_table(u'partners_pca', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('result_structure', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['reports.ResultStructure'], null=True, blank=True)),
            ('number', self.gf('django.db.models.fields.CharField')(max_length=45L, blank=True)),
            ('title', self.gf('django.db.models.fields.CharField')(max_length=256L)),
            ('status', self.gf('django.db.models.fields.CharField')(default=u'in_process', max_length=32L, blank=True)),
            ('partner', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['partners.PartnerOrganization'])),
            ('start_date', self.gf('django.db.models.fields.DateField')(null=True, blank=True)),
            ('end_date', self.gf('django.db.models.fields.DateField')(null=True, blank=True)),
            ('initiation_date', self.gf('django.db.models.fields.DateField')()),
            ('signed_by_unicef_date', self.gf('django.db.models.fields.DateField')(null=True, blank=True)),
            ('signed_by_partner_date', self.gf('django.db.models.fields.DateField')(null=True, blank=True)),
            ('unicef_mng_first_name', self.gf('django.db.models.fields.CharField')(max_length=64L, blank=True)),
            ('unicef_mng_last_name', self.gf('django.db.models.fields.CharField')(max_length=64L, blank=True)),
            ('unicef_mng_email', self.gf('django.db.models.fields.CharField')(max_length=128L, blank=True)),
            ('partner_mng_first_name', self.gf('django.db.models.fields.CharField')(max_length=64L, blank=True)),
            ('partner_mng_last_name', self.gf('django.db.models.fields.CharField')(max_length=64L, blank=True)),
            ('partner_mng_email', self.gf('django.db.models.fields.CharField')(max_length=128L, blank=True)),
            ('partner_contribution_budget', self.gf('django.db.models.fields.IntegerField')(default=0, null=True, blank=True)),
            ('unicef_cash_budget', self.gf('django.db.models.fields.IntegerField')(default=0, null=True, blank=True)),
            ('in_kind_amount_budget', self.gf('django.db.models.fields.IntegerField')(default=0, null=True, blank=True)),
            ('cash_for_supply_budget', self.gf('django.db.models.fields.IntegerField')(default=0, null=True, blank=True)),
            ('total_cash', self.gf('django.db.models.fields.IntegerField')(default=0, null=True, blank=True)),
            ('sectors', self.gf('django.db.models.fields.CharField')(max_length=255, null=True, blank=True)),
            ('current', self.gf('django.db.models.fields.BooleanField')(default=True)),
            ('created_at', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('updated_at', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('amendment', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('amended_at', self.gf('django.db.models.fields.DateTimeField')(null=True)),
            ('amendment_number', self.gf('django.db.models.fields.IntegerField')(default=0)),
            ('original', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['partners.PCA'], null=True)),
        ))
        db.send_create_signal(u'partners', ['PCA'])

        # Adding model 'PCAGrant'
        db.create_table(u'partners_pcagrant', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('pca', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['partners.PCA'])),
            ('grant', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['funds.Grant'])),
            ('funds', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
        ))
        db.send_create_signal(u'partners', ['PCAGrant'])

        # Adding model 'GwPCALocation'
        db.create_table(u'partners_gwpcalocation', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('pca', self.gf('django.db.models.fields.related.ForeignKey')(related_name='locations', to=orm['partners.PCA'])),
            ('governorate', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['locations.Governorate'])),
            ('region', self.gf('smart_selects.db_fields.ChainedForeignKey')(to=orm['locations.Region'])),
            ('locality', self.gf('smart_selects.db_fields.ChainedForeignKey')(to=orm['locations.Locality'])),
            ('gateway', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['locations.GatewayType'], null=True, blank=True)),
            ('location', self.gf('smart_selects.db_fields.ChainedForeignKey')(to=orm['locations.Location'])),
        ))
        db.send_create_signal(u'partners', ['GwPCALocation'])

        # Adding model 'PCASector'
        db.create_table(u'partners_pcasector', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('pca', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['partners.PCA'])),
            ('sector', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['reports.Sector'])),
        ))
        db.send_create_signal(u'partners', ['PCASector'])

        # Adding model 'PCASectorOutput'
        db.create_table(u'partners_pcasectoroutput', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('pca_sector', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['partners.PCASector'])),
            ('output', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['reports.Rrp5Output'])),
        ))
        db.send_create_signal(u'partners', ['PCASectorOutput'])

        # Adding model 'PCASectorGoal'
        db.create_table(u'partners_pcasectorgoal', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('pca_sector', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['partners.PCASector'])),
            ('goal', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['reports.Goal'])),
        ))
        db.send_create_signal(u'partners', ['PCASectorGoal'])

        # Adding model 'PCASectorActivity'
        db.create_table(u'partners_pcasectoractivity', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('pca_sector', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['partners.PCASector'])),
            ('activity', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['reports.Activity'])),
        ))
        db.send_create_signal(u'partners', ['PCASectorActivity'])

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
            ('current', self.gf('django.db.models.fields.IntegerField')(default=0, null=True, blank=True)),
        ))
        db.send_create_signal(u'partners', ['IndicatorProgress'])

        # Adding model 'FileType'
        db.create_table(u'partners_filetype', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(unique=True, max_length=64L)),
        ))
        db.send_create_signal(u'partners', ['FileType'])

        # Adding model 'PCAFile'
        db.create_table(u'partners_pcafile', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('pca', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['partners.PCA'])),
            ('type', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['partners.FileType'])),
            ('file', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['filer.File'])),
        ))
        db.send_create_signal(u'partners', ['PCAFile'])

        # Adding model 'PCAReport'
        db.create_table(u'partners_pcareport', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('pca', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['partners.PCA'])),
            ('title', self.gf('django.db.models.fields.CharField')(max_length=128L)),
            ('description', self.gf('django.db.models.fields.CharField')(max_length=512L)),
            ('start_period', self.gf('django.db.models.fields.DateField')(null=True, blank=True)),
            ('end_period', self.gf('django.db.models.fields.DateField')(null=True, blank=True)),
            ('received_date', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
        ))
        db.send_create_signal(u'partners', ['PCAReport'])


    def backwards(self, orm):
        # Deleting model 'PartnerOrganization'
        db.delete_table(u'partners_partnerorganization')

        # Deleting model 'PCA'
        db.delete_table(u'partners_pca')

        # Deleting model 'PCAGrant'
        db.delete_table(u'partners_pcagrant')

        # Deleting model 'GwPCALocation'
        db.delete_table(u'partners_gwpcalocation')

        # Deleting model 'PCASector'
        db.delete_table(u'partners_pcasector')

        # Deleting model 'PCASectorOutput'
        db.delete_table(u'partners_pcasectoroutput')

        # Deleting model 'PCASectorGoal'
        db.delete_table(u'partners_pcasectorgoal')

        # Deleting model 'PCASectorActivity'
        db.delete_table(u'partners_pcasectoractivity')

        # Deleting model 'PCASectorImmediateResult'
        db.delete_table(u'partners_pcasectorimmediateresult')

        # Removing M2M table for field wbs_activities on 'PCASectorImmediateResult'
        db.delete_table(db.shorten_name(u'partners_pcasectorimmediateresult_wbs_activities'))

        # Deleting model 'IndicatorProgress'
        db.delete_table(u'partners_indicatorprogress')

        # Deleting model 'FileType'
        db.delete_table(u'partners_filetype')

        # Deleting model 'PCAFile'
        db.delete_table(u'partners_pcafile')

        # Deleting model 'PCAReport'
        db.delete_table(u'partners_pcareport')


    models = {
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Group']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Permission']"}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'filer.file': {
            'Meta': {'object_name': 'File'},
            '_file_size': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'file': ('django.db.models.fields.files.FileField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'folder': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'all_files'", 'null': 'True', 'to': "orm['filer.Folder']"}),
            'has_all_mandatory_data': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_public': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'blank': 'True'}),
            'original_filename': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'owned_files'", 'null': 'True', 'to': u"orm['auth.User']"}),
            'polymorphic_ctype': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'polymorphic_filer.file_set'", 'null': 'True', 'to': u"orm['contenttypes.ContentType']"}),
            'sha1': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '40', 'blank': 'True'}),
            'uploaded_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'})
        },
        'filer.folder': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('parent', 'name'),)", 'object_name': 'Folder'},
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'level': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'lft': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'filer_owned_folders'", 'null': 'True', 'to': u"orm['auth.User']"}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'children'", 'null': 'True', 'to': "orm['filer.Folder']"}),
            'rght': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'tree_id': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'uploaded_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'})
        },
        u'funds.donor': {
            'Meta': {'object_name': 'Donor'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '45L'})
        },
        u'funds.grant': {
            'Meta': {'object_name': 'Grant'},
            'donor': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['funds.Donor']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '128L'})
        },
        u'locations.gatewaytype': {
            'Meta': {'object_name': 'GatewayType'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '64L'})
        },
        u'locations.governorate': {
            'Meta': {'object_name': 'Governorate'},
            'area': ('django.contrib.gis.db.models.fields.PolygonField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '45L'})
        },
        u'locations.locality': {
            'Meta': {'unique_together': "(('name', 'cas_code_un'),)", 'object_name': 'Locality'},
            'area': ('django.contrib.gis.db.models.fields.PolygonField', [], {'null': 'True', 'blank': 'True'}),
            'cad_code': ('django.db.models.fields.CharField', [], {'max_length': '11L'}),
            'cas_code': ('django.db.models.fields.CharField', [], {'max_length': '11L'}),
            'cas_code_un': ('django.db.models.fields.CharField', [], {'max_length': '11L'}),
            'cas_village_name': ('django.db.models.fields.CharField', [], {'max_length': '128L'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '128L'}),
            'region': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['locations.Region']"})
        },
        u'locations.location': {
            'Meta': {'unique_together': "(('name', 'p_code'),)", 'object_name': 'Location'},
            'gateway': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['locations.GatewayType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'latitude': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'locality': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['locations.Locality']"}),
            'longitude': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '254L'}),
            'p_code': ('django.db.models.fields.CharField', [], {'max_length': '32L', 'null': 'True', 'blank': 'True'}),
            'point': ('django.contrib.gis.db.models.fields.PointField', [], {})
        },
        u'locations.region': {
            'Meta': {'object_name': 'Region'},
            'area': ('django.contrib.gis.db.models.fields.PolygonField', [], {'null': 'True', 'blank': 'True'}),
            'governorate': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['locations.Governorate']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '45L'})
        },
        u'partners.filetype': {
            'Meta': {'object_name': 'FileType'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '64L'})
        },
        u'partners.gwpcalocation': {
            'Meta': {'object_name': 'GwPCALocation'},
            'gateway': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['locations.GatewayType']", 'null': 'True', 'blank': 'True'}),
            'governorate': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['locations.Governorate']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'locality': ('smart_selects.db_fields.ChainedForeignKey', [], {'to': u"orm['locations.Locality']"}),
            'location': ('smart_selects.db_fields.ChainedForeignKey', [], {'to': u"orm['locations.Location']"}),
            'pca': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'locations'", 'to': u"orm['partners.PCA']"}),
            'region': ('smart_selects.db_fields.ChainedForeignKey', [], {'to': u"orm['locations.Region']"})
        },
        u'partners.indicatorprogress': {
            'Meta': {'object_name': 'IndicatorProgress'},
            'current': ('django.db.models.fields.IntegerField', [], {'default': '0', 'null': 'True', 'blank': 'True'}),
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
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '45L'}),
            'phone_number': ('django.db.models.fields.CharField', [], {'max_length': '32L', 'blank': 'True'})
        },
        u'partners.pca': {
            'Meta': {'object_name': 'PCA'},
            'amended_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'amendment': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'amendment_number': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'cash_for_supply_budget': ('django.db.models.fields.IntegerField', [], {'default': '0', 'null': 'True', 'blank': 'True'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'current': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'end_date': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'in_kind_amount_budget': ('django.db.models.fields.IntegerField', [], {'default': '0', 'null': 'True', 'blank': 'True'}),
            'initiation_date': ('django.db.models.fields.DateField', [], {}),
            'number': ('django.db.models.fields.CharField', [], {'max_length': '45L', 'blank': 'True'}),
            'original': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['partners.PCA']", 'null': 'True'}),
            'partner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['partners.PartnerOrganization']"}),
            'partner_contribution_budget': ('django.db.models.fields.IntegerField', [], {'default': '0', 'null': 'True', 'blank': 'True'}),
            'partner_mng_email': ('django.db.models.fields.CharField', [], {'max_length': '128L', 'blank': 'True'}),
            'partner_mng_first_name': ('django.db.models.fields.CharField', [], {'max_length': '64L', 'blank': 'True'}),
            'partner_mng_last_name': ('django.db.models.fields.CharField', [], {'max_length': '64L', 'blank': 'True'}),
            'result_structure': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['reports.ResultStructure']", 'null': 'True', 'blank': 'True'}),
            'sectors': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'signed_by_partner_date': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'signed_by_unicef_date': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'start_date': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'status': ('django.db.models.fields.CharField', [], {'default': "u'in_process'", 'max_length': '32L', 'blank': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '256L'}),
            'total_cash': ('django.db.models.fields.IntegerField', [], {'default': '0', 'null': 'True', 'blank': 'True'}),
            'unicef_cash_budget': ('django.db.models.fields.IntegerField', [], {'default': '0', 'null': 'True', 'blank': 'True'}),
            'unicef_mng_email': ('django.db.models.fields.CharField', [], {'max_length': '128L', 'blank': 'True'}),
            'unicef_mng_first_name': ('django.db.models.fields.CharField', [], {'max_length': '64L', 'blank': 'True'}),
            'unicef_mng_last_name': ('django.db.models.fields.CharField', [], {'max_length': '64L', 'blank': 'True'}),
            'updated_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        },
        u'partners.pcafile': {
            'Meta': {'object_name': 'PCAFile'},
            'file': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['filer.File']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'pca': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['partners.PCA']"}),
            'type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['partners.FileType']"})
        },
        u'partners.pcagrant': {
            'Meta': {'ordering': "['-funds']", 'object_name': 'PCAGrant'},
            'funds': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'grant': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['funds.Grant']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'pca': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['partners.PCA']"})
        },
        u'partners.pcareport': {
            'Meta': {'object_name': 'PCAReport'},
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
            'sector': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['reports.Sector']"})
        },
        u'partners.pcasectoractivity': {
            'Meta': {'object_name': 'PCASectorActivity'},
            'activity': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['reports.Activity']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'pca_sector': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['partners.PCASector']"})
        },
        u'partners.pcasectorgoal': {
            'Meta': {'object_name': 'PCASectorGoal'},
            'goal': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['reports.Goal']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'pca_sector': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['partners.PCASector']"})
        },
        u'partners.pcasectorimmediateresult': {
            'Intermediate_result': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['reports.IntermediateResult']"}),
            'Meta': {'object_name': 'PCASectorImmediateResult'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'pca_sector': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['partners.PCASector']"}),
            'wbs_activities': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['reports.WBS']", 'symmetrical': 'False'})
        },
        u'partners.pcasectoroutput': {
            'Meta': {'object_name': 'PCASectorOutput'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'output': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['reports.Rrp5Output']"}),
            'pca_sector': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['partners.PCASector']"})
        },
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
            'in_activity_info': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
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

    complete_apps = ['partners']