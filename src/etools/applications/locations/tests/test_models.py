
from django.test import SimpleTestCase
from django.utils import six

from etools.applications.locations.tests.factories import CartoDBTableFactory, GatewayTypeFactory, LocationFactory


class TestStrUnicode(SimpleTestCase):
    '''Ensure calling six.text_type() on model instances returns the right text.'''

    def test_gateway_type(self):
        gateway_type = GatewayTypeFactory.build(name='xyz')
        self.assertEqual(six.text_type(gateway_type), u'xyz')

        gateway_type = GatewayTypeFactory.build(name=u'R\xe4dda Barnen')
        self.assertEqual(six.text_type(gateway_type), u'R\xe4dda Barnen')

    def test_location(self):
        # Test with unicode gateway name
        gateway_type = GatewayTypeFactory.build(name=u'xyz')
        location = LocationFactory.build(gateway=gateway_type, name=u'R\xe4dda Barnen', p_code='abc')
        self.assertEqual(six.text_type(location), u'R\xe4dda Barnen (xyz PCode: abc)')

        # Test with str gateway name
        gateway_type = GatewayTypeFactory.build(name='xyz')
        location = LocationFactory.build(gateway=gateway_type, name=u'R\xe4dda Barnen', p_code='abc')
        self.assertEqual(six.text_type(location), u'R\xe4dda Barnen (xyz PCode: abc)')

    def test_carto_db_table(self):
        carto_db_table = CartoDBTableFactory.build(table_name=u'R\xe4dda Barnen')
        self.assertEqual(six.text_type(carto_db_table), u'R\xe4dda Barnen')

        carto_db_table = CartoDBTableFactory.build(table_name='xyz')
        self.assertEqual(six.text_type(carto_db_table), u'xyz')
