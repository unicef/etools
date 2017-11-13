from __future__ import absolute_import, division, print_function

import os

from django.core.exceptions import SuspiciousFileOperation
from django.core.files.storage import get_storage_class
from django.utils.crypto import get_random_string
from django.utils.functional import LazyObject


class SaveNameStorageMixin(object):
    def get_available_name(self, name, max_length=None):
        """
        Returns a filename that's free on the target storage system, and
        available for new content to be written to.
        """
        dir_name, file_name = os.path.split(name)
        file_root, file_ext = os.path.splitext(file_name)
        # If the filename already exists, create random name directory and put file to it.
        # Truncate original name if required, so the new filename does not exceed the max_length.
        while self.exists(name) or (max_length and len(name) > max_length):
            # file_ext includes the dot.
            name = os.path.join(dir_name, get_random_string(7), "%s%s" % (file_root, file_ext))
            if max_length is None:
                continue
            # Truncate file_root if max_length exceeded.
            truncation = len(name) - max_length
            if truncation > 0:
                file_root = file_root[:-truncation]
                # Entire file_root was truncated in attempt to find an available filename.
                if not file_root:
                    raise SuspiciousFileOperation(
                        'Storage can not find an available filename for "%s". '
                        'Please make sure that the corresponding file field '
                        'allows sufficient "max_length".' % name
                    )
                name = os.path.join(dir_name, get_random_string(7), "%s%s" % (file_root, file_ext))
        return name


class SaveNameDefaultStorage(LazyObject):
    def _setup(self):
        self._wrapped = type('SaveNameDefaultStorage', (SaveNameStorageMixin, get_storage_class()), {})()


save_name_default_storage = SaveNameDefaultStorage()
