__author__ = 'jcranwellward'

import os

from django.conf import settings
from django.core.management.base import (
    BaseCommand,
    CommandError
)

from filer import models as filer_models

from tracker.models import PCA as OLDPCA
from partners.models import (
    PCA,
    FileType,
    PCAFile
)


class Command(BaseCommand):
    """

    """
    can_import_settings = True

    def handle(self, *args, **options):

        files = filer_models.File.objects.all()
        count = files.count()
        for num, file in enumerate(files):
            file.is_public = False
            file.save()
            print "Moved file ({} of {}): {}".format(
                num+1,
                count,
                file.name
            )