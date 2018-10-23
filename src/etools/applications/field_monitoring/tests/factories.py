from django.contrib.auth.models import Group
from django.contrib.gis.geos import Point

import factory
from factory import fuzzy

from unicef_locations.tests.factories import LocationFactory

from etools.applications.field_monitoring.models import MethodType, UNICEFUser, Site, CPOutputConfig
from etools.applications.field_monitoring_shared.models import Method
from etools.applications.firms.tests.factories import BaseUserFactory
from etools.applications.partners.models import PartnerType
from etools.applications.partners.tests.factories import PartnerFactory, InterventionResultLinkFactory
from etools.applications.reports.models import ResultType
from etools.applications.reports.tests.factories import ResultFactory


class UserFactory(BaseUserFactory):
    """
    User factory with ability to quickly assign auditor portal related groups with special logic for auditor.
    """
    class Params:
        unicef_user = factory.Trait(
            groups=[UNICEFUser.name],
        )

    @factory.post_generation
    def groups(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted is not None:
            extracted = extracted[:]
            for i, group in enumerate(extracted):
                if isinstance(group, str):
                    extracted[i] = Group.objects.get_or_create(name=group)[0]

            self.groups.add(*extracted)


class MethodFactory(factory.DjangoModelFactory):
    name = fuzzy.FuzzyText()

    class Meta:
        model = Method


class MethodTypeFactory(factory.DjangoModelFactory):
    method = factory.SubFactory(MethodFactory, is_types_applicable=True)
    name = fuzzy.FuzzyText()

    class Meta:
        model = MethodType


class SiteFactory(LocationFactory):
    security_detail = fuzzy.FuzzyText()
    parent = factory.SubFactory(LocationFactory)
    gateway = None
    point = Point(x=10, y=10)

    class Meta:
        model = Site


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
