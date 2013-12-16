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

    def handle(self, path, **options):

        for dirpath, dnames, fnames in os.walk(path):

            for file_name in fnames:

                parts = os.path.split(dirpath)
                pca_id = os.path.basename(parts[-2])
                file_type = parts[-1]

                relpath = "{}/{}/".format(
                    pca_id, file_type
                )

                old_pca = OLDPCA.objects.get(pca_id=pca_id)
                new_pca = PCA.objects.get(number=old_pca.number)

                partner_folder, created = filer_models.Folder.objects.get_or_create(
                    name=new_pca.partner.name,
                )
                pca_folder, created = filer_models.Folder.objects.get_or_create(
                    name=new_pca.number,
                    parent=partner_folder,
                )
                type_folder, created = filer_models.Folder.objects.get_or_create(
                    name=file_type,
                    parent=pca_folder,
                )
                file, created = filer_models.File.objects.get_or_create(
                    file=os.path.join(os.path.join('filer_public/pcas/', relpath), file_name)
                )
                if created:
                    print "Created"
                file.name = file_name
                file.folder = type_folder
                file.is_public = True
                file.save()

                print file.path

                file_type, created = FileType.objects.get_or_create(name=file_type)
                pca_file, created = PCAFile.objects.get_or_create(
                    pca=new_pca,
                    type=file_type,
                    file=file
                )

                if created:
                    print "PCA file created: {}".format(file.name)
