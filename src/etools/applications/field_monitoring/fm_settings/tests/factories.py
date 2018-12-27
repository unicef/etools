from django.contrib.gis.geos import GEOSGeometry

import factory
from factory import fuzzy

from unicef_locations.models import GatewayType
from unicef_locations.tests.factories import LocationFactory

from etools.applications.attachments.tests.factories import AttachmentFactory
from etools.applications.field_monitoring.fm_settings.models import FMMethodType, LocationSite, CPOutputConfig, \
    CheckListCategory, CheckListItem, PlannedCheckListItem, PlannedCheckListItemPartnerInfo, LogIssue
from etools.applications.field_monitoring.shared.models import FMMethod
from etools.applications.partners.models import PartnerType
from etools.applications.partners.tests.factories import PartnerFactory, InterventionResultLinkFactory
from etools.applications.reports.models import ResultType, CountryProgramme
from etools.applications.reports.tests.factories import ResultFactory, CountryProgrammeFactory, SectionFactory
from etools.applications.users.tests.factories import UserFactory


class FMMethodFactory(factory.DjangoModelFactory):
    name = fuzzy.FuzzyText()

    class Meta:
        model = FMMethod


class FMMethodTypeFactory(factory.DjangoModelFactory):
    method = factory.SubFactory(FMMethodFactory, is_types_applicable=True)
    name = fuzzy.FuzzyText()

    class Meta:
        model = FMMethodType


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

    interventions__count = 1
    government_partners__count = 1
    sections__count = 0

    class Meta:
        model = CPOutputConfig
        django_get_or_create = ("cp_output", )

    @factory.post_generation
    def cp_output_country_programme(self, *args, **kwargs):
        country_programme = CountryProgramme.objects.first()
        if not country_programme:
            country_programme = CountryProgrammeFactory()

        self.cp_output.country_programme = country_programme
        self.cp_output.save()

    @factory.post_generation
    def interventions(self, created, extracted, count, **kwargs):
        if created:
            [InterventionResultLinkFactory(cp_output=self.cp_output) for i in range(count)]

    @factory.post_generation
    def government_partners(self, created, extracted, count, **kwargs):
        if created:
            self.government_partners.add(*[PartnerFactory(partner_type=PartnerType.GOVERNMENT) for i in range(count)])

        if extracted:
            self.government_partners.add(*extracted)

    @factory.post_generation
    def sections(self, created, extracted, count, **kwargs):
        if created:
            self.sections.add(*[SectionFactory() for i in range(count)])

        if extracted:
            self.sections.add(*extracted)


class CheckListCategoryFactory(factory.DjangoModelFactory):
    name = fuzzy.FuzzyText()

    class Meta:
        model = CheckListCategory


class CheckListItemFactory(factory.DjangoModelFactory):
    category = factory.SubFactory(CheckListCategoryFactory)
    question_number = factory.Sequence(lambda n: str(n))
    question_text = fuzzy.FuzzyText()

    class Meta:
        model = CheckListItem


class PlannedCheckListItemFactory(factory.DjangoModelFactory):
    checklist_item = factory.SubFactory(CheckListItemFactory)
    cp_output_config = factory.SubFactory(CPOutputConfigFactory)

    class Meta:
        model = PlannedCheckListItem

    methods__count = 0
    partners_info__count = 0

    @factory.post_generation
    def methods(self, created, extracted, count, **kwargs):
        if extracted:
            self.methods.add(*extracted)
        elif created:
            self.methods.add(*[FMMethodFactory() for i in range(count)])

    @factory.post_generation
    def partners_info(self, created, extracted, count, **kwargs):
        if created:
            for i in range(count):
                PlannedCheckListItemPartnerInfoFactory(planned_checklist_item=self)


class PlannedCheckListItemPartnerInfoFactory(factory.DjangoModelFactory):
    planned_checklist_item = factory.SubFactory(PlannedCheckListItemFactory)
    partner = factory.SubFactory(PartnerFactory)
    specific_details = fuzzy.FuzzyText()
    standard_url = fuzzy.FuzzyText()

    class Meta:
        model = PlannedCheckListItemPartnerInfo


class LogIssueFactory(factory.DjangoModelFactory):
    author = factory.SubFactory(UserFactory)
    issue = fuzzy.FuzzyText()

    attachments__count = 0

    class Meta:
        model = LogIssue

    @factory.post_generation
    def attachments(self, create, extracted, count, **kwargs):
        if not create:
            return

        for i in range(count):
            AttachmentFactory(content_object=self)
