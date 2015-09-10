# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):

        # Changing field 'UserProfile.phone_number'
        db.alter_column(u'users_userprofile', 'phone_number', self.gf('django.db.models.fields.CharField')(max_length=20, null=True))

        # Changing field 'UserProfile.office'
        db.alter_column(u'users_userprofile', 'office_id', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['trips.Office'], null=True))

        # Changing field 'UserProfile.section'
        db.alter_column(u'users_userprofile', 'section_id', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['reports.Sector'], null=True))

        # Changing field 'UserProfile.job_title'
        db.alter_column(u'users_userprofile', 'job_title', self.gf('django.db.models.fields.CharField')(max_length=255, null=True))

    def backwards(self, orm):

        # User chose to not deal with backwards NULL issues for 'UserProfile.phone_number'
        raise RuntimeError("Cannot reverse this migration. 'UserProfile.phone_number' and its values cannot be restored.")
        
        # The following code is provided here to aid in writing a correct migration
        # Changing field 'UserProfile.phone_number'
        db.alter_column(u'users_userprofile', 'phone_number', self.gf('django.db.models.fields.CharField')(max_length=20))

        # User chose to not deal with backwards NULL issues for 'UserProfile.office'
        raise RuntimeError("Cannot reverse this migration. 'UserProfile.office' and its values cannot be restored.")
        
        # The following code is provided here to aid in writing a correct migration
        # Changing field 'UserProfile.office'
        db.alter_column(u'users_userprofile', 'office_id', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['trips.Office']))

        # User chose to not deal with backwards NULL issues for 'UserProfile.section'
        raise RuntimeError("Cannot reverse this migration. 'UserProfile.section' and its values cannot be restored.")
        
        # The following code is provided here to aid in writing a correct migration
        # Changing field 'UserProfile.section'
        db.alter_column(u'users_userprofile', 'section_id', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['reports.Sector']))

        # User chose to not deal with backwards NULL issues for 'UserProfile.job_title'
        raise RuntimeError("Cannot reverse this migration. 'UserProfile.job_title' and its values cannot be restored.")
        
        # The following code is provided here to aid in writing a correct migration
        # Changing field 'UserProfile.job_title'
        db.alter_column(u'users_userprofile', 'job_title', self.gf('django.db.models.fields.CharField')(max_length=255))

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
            'Meta': {'ordering': "['first_name']", 'object_name': 'User'},
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
        u'registration.registrationprofile': {
            'Meta': {'object_name': 'RegistrationProfile'},
            'activation_key': ('django.db.models.fields.CharField', [], {'max_length': '40'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']", 'unique': 'True'})
        },
        u'reports.sector': {
            'Meta': {'ordering': "['name']", 'object_name': 'Sector'},
            'alternate_id': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'alternate_name': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'color': ('paintstore.fields.ColorPickerField', [], {'max_length': '7', 'null': 'True', 'blank': 'True'}),
            'dashboard': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'description': ('django.db.models.fields.CharField', [], {'max_length': '256L', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '45L'})
        },
        u'trips.office': {
            'Meta': {'object_name': 'Office'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '254'})
        },
        u'users.equitrackregistrationmodel': {
            'Meta': {'object_name': 'EquiTrackRegistrationModel', '_ormbases': [u'registration.RegistrationProfile']},
            u'registrationprofile_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': u"orm['registration.RegistrationProfile']", 'unique': 'True', 'primary_key': 'True'})
        },
        u'users.userprofile': {
            'Meta': {'object_name': 'UserProfile'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'job_title': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'office': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['trips.Office']", 'null': 'True', 'blank': 'True'}),
            'phone_number': ('django.db.models.fields.CharField', [], {'max_length': '20', 'null': 'True', 'blank': 'True'}),
            'section': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['reports.Sector']", 'null': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'profile'", 'unique': 'True', 'to': u"orm['auth.User']"})
        }
    }

    complete_apps = ['users']