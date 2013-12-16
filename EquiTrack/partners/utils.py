__author__ = 'jcranwellward'

from filer.utils.generate_filename import by_date
from filer.utils.files import get_valid_filename
from django.utils.encoding import force_unicode, smart_str
import datetime
import os


def by_pca(instance, filename):

    if hasattr(instance, 'pcafile_set'):

        pca_file = instance.pcafile_set.all()

        if pca_file.count():

            pca_file = pca_file[0]
            partner = pca_file.pca.partner.name
            pca_number = pca_file.pca.number
            file_type = pca_file.type

            file_path = u'{partner}/{pca}/{type}'.format(
                partner=partner,
                pca=pca_number,
                type=file_type
            )

            file_name = get_valid_filename(instance.name)

            return os.path.join(file_path, file_name)

    return by_date(instance, filename)