from __future__ import absolute_import, division, print_function, unicode_literals

import sys
from unittest import skipIf, TestCase

from django.utils import six

from EquiTrack.factories import CountryFactory
from vision.models import VisionSyncLog


@skipIf(sys.version_info.major == 3, "This test can be deleted under Python 3")
class TestStrUnicode(TestCase):
    '''Ensure calling str() on model instances returns UTF8-encoded text and unicode() returns unicode.'''
    def test_vision_sync_log(self):
        country = CountryFactory.build(name='M\xe9xico', schema_name='Mexico', domain_url='mexico.example.com')
        instance = VisionSyncLog(country=country)
        self.assertTrue(str(instance).startswith(b'M\xc3\xa9xico'))
        self.assertTrue(six.text_type(instance).startswith(u'M\xe9xico'))
