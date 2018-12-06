from django.test import SimpleTestCase

from etools.applications.users.tests.factories import CountryFactory
from etools.applications.vision.models import VisionSyncLog


class TestStrUnicode(SimpleTestCase):
    '''Ensure calling str() on model instances returns the right text.'''

    def test_vision_sync_log(self):
        country = CountryFactory.build(name='M\xe9xico', schema_name='Mexico')
        instance = VisionSyncLog(country=country)
        self.assertTrue(str(instance).startswith(u'M\xe9xico'))
