from __future__ import unicode_literals

from django.db import migrations

from utils.common.migrating import fix_null_values


def fix_nulls(apps, schema):
    # Change null values in these fields to empty strings
    fix_null_values(
        apps.get_model('attachments.attachment'),
        [
            'hyperlink',
        ]
    )


class Migration(migrations.Migration):

    dependencies = [
        (u'attachments', u'0002_attachmentflat_filename'),
    ]

    operations = [
        migrations.RunPython(fix_nulls, migrations.RunPython.noop)
    ]
