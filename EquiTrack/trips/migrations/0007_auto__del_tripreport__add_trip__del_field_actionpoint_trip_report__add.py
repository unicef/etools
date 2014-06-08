# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Deleting model 'TripReport'
        db.delete_table(u'trips_tripreport')

        # Removing M2M table for field partners on 'TripReport'
        db.delete_table(db.shorten_name(u'trips_tripreport_partners'))

        # Removing M2M table for field pcas on 'TripReport'
        db.delete_table(db.shorten_name(u'trips_tripreport_pcas'))

        # Adding model 'Trip'
        db.create_table(u'trips_trip', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('purpose_of_travel', self.gf('django.db.models.fields.CharField')(max_length=254)),
            ('travel_type', self.gf('django.db.models.fields.CharField')(default=u'duty_travel', max_length=32L)),
            ('international_travel', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('from_date', self.gf('django.db.models.fields.DateTimeField')()),
            ('to_date', self.gf('django.db.models.fields.DateTimeField')()),
            ('wbs', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['reports.WBS'], null=True, blank=True)),
            ('grant', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['funds.Grant'], null=True, blank=True)),
            ('monitoring_supply_delivery', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('activities_undertaken', self.gf('django.db.models.fields.CharField')(max_length=254)),
            ('no_pca', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('main_observations', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('status', self.gf('django.db.models.fields.CharField')(default=u'planned', max_length=32L)),
            ('supervisor', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
            ('programme_assistant', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'], null=True, blank=True)),
            ('approved_by_supervisor', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('budget_owner', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
            ('approved_by_budget_owner', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('approved_by_human_resources', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('representative_approval', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('approved_date', self.gf('django.db.models.fields.DateField')(null=True, blank=True)),
        ))
        db.send_create_signal(u'trips', ['Trip'])

        # Adding M2M table for field pcas on 'Trip'
        m2m_table_name = db.shorten_name(u'trips_trip_pcas')
        db.create_table(m2m_table_name, (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('trip', models.ForeignKey(orm[u'trips.trip'], null=False)),
            ('pca', models.ForeignKey(orm[u'partners.pca'], null=False))
        ))
        db.create_unique(m2m_table_name, ['trip_id', 'pca_id'])

        # Adding M2M table for field partners on 'Trip'
        m2m_table_name = db.shorten_name(u'trips_trip_partners')
        db.create_table(m2m_table_name, (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('trip', models.ForeignKey(orm[u'trips.trip'], null=False)),
            ('partnerorganization', models.ForeignKey(orm[u'partners.partnerorganization'], null=False))
        ))
        db.create_unique(m2m_table_name, ['trip_id', 'partnerorganization_id'])

        # Deleting field 'ActionPoint.trip_report'
        db.delete_column(u'trips_actionpoint', 'trip_report_id')

        # Adding field 'ActionPoint.trip'
        db.add_column(u'trips_actionpoint', 'trip',
                      self.gf('django.db.models.fields.related.ForeignKey')(default=1, to=orm['trips.Trip']),
                      keep_default=False)

        # Deleting field 'TravelRoutes.trip_report'
        db.delete_column(u'trips_travelroutes', 'trip_report_id')

        # Adding field 'TravelRoutes.trip'
        db.add_column(u'trips_travelroutes', 'trip',
                      self.gf('django.db.models.fields.related.ForeignKey')(default=1, to=orm['trips.Trip']),
                      keep_default=False)


    def backwards(self, orm):
        # Adding model 'TripReport'
        db.create_table(u'trips_tripreport', (
            ('status', self.gf('django.db.models.fields.CharField')(default=u'planned', max_length=32L)),
            ('main_observations', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('international_travel', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('supervisor', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
            ('budget_owner', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
            ('purpose_of_travel', self.gf('django.db.models.fields.CharField')(max_length=254)),
            ('no_pca', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('approved_date', self.gf('django.db.models.fields.DateField')(null=True, blank=True)),
            ('from_date', self.gf('django.db.models.fields.DateField')()),
            ('activities_undertaken', self.gf('django.db.models.fields.CharField')(max_length=254)),
            ('to_date', self.gf('django.db.models.fields.DateField')()),
            ('human_resources', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'], null=True, blank=True)),
            ('travel_type', self.gf('django.db.models.fields.CharField')(default=u'duty_travel', max_length=32L)),
            ('representative_approval', self.gf('django.db.models.fields.BooleanField')(default=False)),
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
        ))
        db.send_create_signal(u'trips', ['TripReport'])

        # Adding M2M table for field partners on 'TripReport'
        m2m_table_name = db.shorten_name(u'trips_tripreport_partners')
        db.create_table(m2m_table_name, (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('tripreport', models.ForeignKey(orm[u'trips.tripreport'], null=False)),
            ('partnerorganization', models.ForeignKey(orm[u'partners.partnerorganization'], null=False))
        ))
        db.create_unique(m2m_table_name, ['tripreport_id', 'partnerorganization_id'])

        # Adding M2M table for field pcas on 'TripReport'
        m2m_table_name = db.shorten_name(u'trips_tripreport_pcas')
        db.create_table(m2m_table_name, (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('tripreport', models.ForeignKey(orm[u'trips.tripreport'], null=False)),
            ('pca', models.ForeignKey(orm[u'partners.pca'], null=False))
        ))
        db.create_unique(m2m_table_name, ['tripreport_id', 'pca_id'])

        # Deleting model 'Trip'
        db.delete_table(u'trips_trip')

        # Removing M2M table for field pcas on 'Trip'
        db.delete_table(db.shorten_name(u'trips_trip_pcas'))

        # Removing M2M table for field partners on 'Trip'
        db.delete_table(db.shorten_name(u'trips_trip_partners'))


        # User chose to not deal with backwards NULL issues for 'ActionPoint.trip_report'
        raise RuntimeError("Cannot reverse this migration. 'ActionPoint.trip_report' and its values cannot be restored.")
        # Deleting field 'ActionPoint.trip'
        db.delete_column(u'trips_actionpoint', 'trip_id')


        # User chose to not deal with backwards NULL issues for 'TravelRoutes.trip_report'
        raise RuntimeError("Cannot reverse this migration. 'TravelRoutes.trip_report' and its values cannot be restored.")
        # Deleting field 'TravelRoutes.trip'
        db.delete_column(u'trips_travelroutes', 'trip_id')


    models = {
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
        u'activityinfo.partner': {
            'Meta': {'ordering': "['name']", 'object_name': 'Partner'},
            'ai_id': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'database': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['activityinfo.Database']"}),
            'full_name': ('django.db.models.fields.CharField', [], {'max_length': '254', 'null': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '254'})
        },
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
            'Meta': {'ordering': "['name']", 'object_name': 'Donor'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '45L'})
        },
        u'funds.grant': {
            'Meta': {'ordering': "['name']", 'object_name': 'Grant'},
            'donor': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['funds.Donor']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '128L'})
        },
        u'partners.filetype': {
            'Meta': {'object_name': 'FileType'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '64L'})
        },
        u'partners.partnerorganization': {
            'Meta': {'ordering': "['name']", 'object_name': 'PartnerOrganization'},
            'activity_info_partner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['activityinfo.Partner']", 'null': 'True', 'blank': 'True'}),
            'contact_person': ('django.db.models.fields.CharField', [], {'max_length': '64L', 'blank': 'True'}),
            'description': ('django.db.models.fields.CharField', [], {'max_length': '256L', 'blank': 'True'}),
            'email': ('django.db.models.fields.CharField', [], {'max_length': '128L', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '45L'}),
            'phone_number': ('django.db.models.fields.CharField', [], {'max_length': '32L', 'blank': 'True'})
        },
        u'partners.pca': {
            'Meta': {'ordering': "['-number', 'amendment']", 'object_name': 'PCA'},
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
            'unicef_managers': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.User']", 'symmetrical': 'False'}),
            'unicef_mng_email': ('django.db.models.fields.CharField', [], {'max_length': '128L', 'blank': 'True'}),
            'unicef_mng_first_name': ('django.db.models.fields.CharField', [], {'max_length': '64L', 'blank': 'True'}),
            'unicef_mng_last_name': ('django.db.models.fields.CharField', [], {'max_length': '64L', 'blank': 'True'}),
            'updated_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
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
        u'reports.sector': {
            'Meta': {'ordering': "['name']", 'object_name': 'Sector'},
            'description': ('django.db.models.fields.CharField', [], {'max_length': '256L', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '45L'})
        },
        u'reports.wbs': {
            'Intermediate_result': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['reports.IntermediateResult']"}),
            'Meta': {'ordering': "['name']", 'object_name': 'WBS'},
            'code': ('django.db.models.fields.CharField', [], {'max_length': '10L'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '128L'})
        },
        u'trips.actionpoint': {
            'Meta': {'object_name': 'ActionPoint'},
            'completed_date': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.CharField', [], {'max_length': '254'}),
            'due_date': ('django.db.models.fields.DateField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'persons_responsible': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.User']", 'symmetrical': 'False'}),
            'trip': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['trips.Trip']"})
        },
        u'trips.fileattachment': {
            'Meta': {'object_name': 'FileAttachment'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            'file': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['filer.File']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'object_id': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['partners.FileType']"})
        },
        u'trips.travelroutes': {
            'Meta': {'object_name': 'TravelRoutes'},
            'arrive': ('django.db.models.fields.TimeField', [], {}),
            'date': ('django.db.models.fields.DateField', [], {}),
            'depart': ('django.db.models.fields.TimeField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'route': ('django.db.models.fields.CharField', [], {'max_length': '254'}),
            'trip': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['trips.Trip']"})
        },
        u'trips.trip': {
            'Meta': {'ordering': "['-from_date', '-to_date']", 'object_name': 'Trip'},
            'activities_undertaken': ('django.db.models.fields.CharField', [], {'max_length': '254'}),
            'approved_by_budget_owner': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'approved_by_human_resources': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'approved_by_supervisor': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'approved_date': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'budget_owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'from_date': ('django.db.models.fields.DateTimeField', [], {}),
            'grant': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['funds.Grant']", 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'international_travel': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'main_observations': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'monitoring_supply_delivery': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'no_pca': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'partners': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': u"orm['partners.PartnerOrganization']", 'null': 'True', 'blank': 'True'}),
            'pcas': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['partners.PCA']", 'symmetrical': 'False'}),
            'programme_assistant': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']", 'null': 'True', 'blank': 'True'}),
            'purpose_of_travel': ('django.db.models.fields.CharField', [], {'max_length': '254'}),
            'representative_approval': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'status': ('django.db.models.fields.CharField', [], {'default': "u'planned'", 'max_length': '32L'}),
            'supervisor': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'to_date': ('django.db.models.fields.DateTimeField', [], {}),
            'travel_type': ('django.db.models.fields.CharField', [], {'default': "u'duty_travel'", 'max_length': '32L'}),
            'wbs': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['reports.WBS']", 'null': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['trips']