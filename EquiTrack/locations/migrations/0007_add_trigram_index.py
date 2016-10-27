# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('locations', '0006_auto_20160229_1545'),
    ]

    operations = [
        migrations.RunSQL(
            sql="CREATE EXTENSION IF NOT EXISTS pg_trgm WITH SCHEMA pg_catalog",
            reverse_sql="DROP EXTENSION IF EXISTS pg_trgm CASCADE",
        ),
        migrations.RunSQL(
            sql="CREATE INDEX IF NOT EXISTS index_locations_on_name_trigram on locations_location USING gin (name gin_trgm_ops)",
            reverse_sql="DROP INDEX IF EXISTS index_locations_on_name_trigram"
        ),
    ]