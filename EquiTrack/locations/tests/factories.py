from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from django.contrib.gis.geos import GEOSGeometry
import factory

from locations import models


class GatewayTypeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.GatewayType

    name = factory.Sequence(lambda n: 'GatewayType {}'.format(n))
    admin_level = factory.Sequence(lambda n: n)


class LocationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.Location

    name = factory.Sequence(lambda n: 'Location {}'.format(n))
    gateway = factory.SubFactory(GatewayTypeFactory)
    point = GEOSGeometry("POINT(20 20)")
    p_code = factory.Sequence(lambda n: 'PCODE{}'.format(n))


class CartoDBTableFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.CartoDBTable

    domain = factory.Sequence(lambda n: 'Domain {}'.format(n))
    api_key = factory.Sequence(lambda n: 'API Key {}'.format(n))
    table_name = factory.Sequence(lambda n: 'table_name_{}'.format(n))
    location_type = factory.SubFactory(GatewayTypeFactory)
    domain = factory.Sequence(lambda n: 'Domain {}'.format(n))
