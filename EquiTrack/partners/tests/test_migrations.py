from __future__ import unicode_literals

from django.db import migrations
from django.contrib.postgres.operations import HStoreExtension


class Migration(migrations.Migration):

    operations = [
        HStoreExtension(),
    ]