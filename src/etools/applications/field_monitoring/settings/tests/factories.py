from django.contrib.gis.geos import GEOSGeometry

import factory
from factory import fuzzy

from unicef_locations.models import GatewayType
from unicef_locations.tests.factories import LocationFactory

from etools.applications.field_monitoring.settings.models import MethodType, LocationSite, CPOutputConfig
from etools.applications.field_monitoring.shared.models import Method
from etools.applications.partners.models import PartnerType
from etools.applications.partners.tests.factories import PartnerFactory, InterventionResultLinkFactory
from etools.applications.reports.models import ResultType
from etools.applications.reports.tests.factories import ResultFactory


class MethodFactory(factory.DjangoModelFactory):
    name = fuzzy.FuzzyText()

    class Meta:
        model = Method


class MethodTypeFactory(factory.DjangoModelFactory):
    method = factory.SubFactory(MethodFactory, is_types_applicable=True)
    name = fuzzy.FuzzyText()

    class Meta:
        model = MethodType


class LocationSiteFactory(factory.DjangoModelFactory):
    name = factory.Sequence(lambda n: 'Location {}'.format(n))
    point = GEOSGeometry("POINT(20 20)")
    p_code = factory.Sequence(lambda n: 'PCODE{}'.format(n))
    security_detail = fuzzy.FuzzyText()
    parent = factory.LazyAttribute(lambda o:
                                   LocationFactory(gateway=GatewayType.objects.get_or_create(admin_level=0)[0]))

    class Meta:
        model = LocationSite


class CPOutputConfigFactory(factory.DjangoModelFactory):
    cp_output = factory.SubFactory(ResultFactory, result_type__name=ResultType.OUTPUT)
    is_monitored = True
    is_priority = True

    class Meta:
        model = CPOutputConfig

    @factory.post_generation
    def interventions(self, created, extracted, **kwargs):
        if created:
            [InterventionResultLinkFactory(cp_output=self.cp_output) for i in range(3)]

    @factory.post_generation
    def government_partners(self, created, extracted, **kwargs):
        if created:
            self.government_partners.add(*[PartnerFactory(partner_type=PartnerType.GOVERNMENT) for i in range(3)])

        if extracted:
            self.government_partners.add(*extracted)
