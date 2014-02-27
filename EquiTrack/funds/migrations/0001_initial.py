# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Donor'
        db.create_table(u'funds_donor', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(unique=True, max_length=45L)),
        ))
        db.send_create_signal(u'funds', ['Donor'])

        # Adding model 'Grant'
        db.create_table(u'funds_grant', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('donor', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['funds.Donor'])),
            ('name', self.gf('django.db.models.fields.CharField')(unique=True, max_length=128L)),
        ))
        db.send_create_signal(u'funds', ['Grant'])


    def backwards(self, orm):
        # Deleting model 'Donor'
        db.delete_table(u'funds_donor')

        # Deleting model 'Grant'
        db.delete_table(u'funds_grant')


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