# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding unique constraint on 'Donor', fields ['name']
        db.create_unique(u'funds_donor', ['name'])

        # Adding unique constraint on 'Grant', fields ['name']
        db.create_unique(u'funds_grant', ['name'])


    def backwards(self, orm):
        # Removing unique constraint on 'Grant', fields ['name']
        db.delete_unique(u'funds_grant', ['name'])

        # Removing unique constraint on 'Donor', fields ['name']
        db.delete_unique(u'funds_donor', ['name'])


    models = {
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
        }
    }

    complete_apps = ['funds']