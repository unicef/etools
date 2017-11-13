from __future__ import absolute_import, division, print_function, unicode_literals

import sys
from unittest import skipIf, TestCase

from EquiTrack.factories import CartoDBTableFactory, GatewayTypeFactory, LocationFactory


@skipIf(sys.version_info.major == 3, "This test can be deleted under Python 3")
class TestStrUnicode(TestCase):
    '''Ensure calling str() on model instances returns UTF8-encoded text and unicode() returns unicode.'''
    def test_gateway_type(self):
        gateway_type = GatewayTypeFactory.build(name=b'xyz')
        self.assertEqual(str(gateway_type), b'xyz')
        self.assertEqual(unicode(gateway_type), u'xyz')

        gateway_type = GatewayTypeFactory.build(name=u'R\xe4dda Barnen')
        self.assertEqual(str(gateway_type), b'R\xc3\xa4dda Barnen')
        self.assertEqual(unicode(gateway_type), u'R\xe4dda Barnen')

    def test_location(self):
        # Test with unicode gateway name
        gateway_type = GatewayTypeFactory.build(name=u'xyz')
        location = LocationFactory.build(gateway=gateway_type, name=u'R\xe4dda Barnen', p_code='abc')
        self.assertEqual(str(location), b'R\xc3\xa4dda Barnen (xyz PCode: abc)')
        self.assertEqual(unicode(location), u'R\xe4dda Barnen (xyz PCode: abc)')

        # Test with str gateway name
        gateway_type = GatewayTypeFactory.build(name=b'xyz')
        location = LocationFactory.build(gateway=gateway_type, name=u'R\xe4dda Barnen', p_code='abc')
        self.assertEqual(str(location), b'R\xc3\xa4dda Barnen (xyz PCode: abc)')
        self.assertEqual(unicode(location), u'R\xe4dda Barnen (xyz PCode: abc)')

    def test_carto_db_table(self):
        carto_db_table = CartoDBTableFactory.build(table_name=u'R\xe4dda Barnen')
        self.assertEqual(str(carto_db_table), b'R\xc3\xa4dda Barnen')
        self.assertEqual(unicode(carto_db_table), u'R\xe4dda Barnen')

        carto_db_table = CartoDBTableFactory.build(table_name=b'xyz')
        self.assertEqual(str(carto_db_table), b'xyz')
        self.assertEqual(unicode(carto_db_table), u'xyz')
