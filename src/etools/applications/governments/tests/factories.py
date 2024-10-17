import datetime

import factory
from factory import fuzzy
from unicef_locations.tests.factories import LocationFactory

from etools.applications.attachments.tests.factories import AttachmentFactory
from etools.applications.field_monitoring.fm_settings.tests.factories import LocationSiteFactory
from etools.applications.governments import models
from etools.applications.organizations.models import OrganizationType
from etools.applications.organizations.tests.factories import OrganizationFactory
from etools.applications.partners.tests.factories import FileTypeFactory, PartnerFactory
from etools.applications.reports.tests.factories import CountryProgrammeFactory, ResultFactory
from etools.applications.users.tests.factories import UserFactory


class GovernmentEWPFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.GovernmentEWP

    country_programme = factory.SubFactory(CountryProgrammeFactory)


class EWPOutputFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.EWPOutput

    workplan = factory.SubFactory(GovernmentEWPFactory)
    cp_output = factory.SubFactory(ResultFactory)


class EWPKeyInterventionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.EWPKeyIntervention

    ewp_output = factory.SubFactory(EWPOutputFactory)
    cp_key_intervention = factory.SubFactory(ResultFactory)


class EWPActivityFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.EWPActivity

    workplan = factory.SubFactory(GovernmentEWPFactory)
    ewp_key_intervention = factory.SubFactory(EWPKeyInterventionFactory)

    @factory.post_generation
    def locations(self, create, extracted, **kwargs):
        location = LocationFactory()
        self.locations.add(location)


class GDDFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.GDD

    partner = factory.SubFactory(PartnerFactory, organization__organization_type=OrganizationType.GOVERNMENT)
    country_programme = factory.SubFactory(CountryProgrammeFactory)
    title = factory.Sequence(lambda n: 'GDD Title {}'.format(n))
    submission_date = datetime.datetime.today()
    reference_number_year = datetime.date.today().year
    start = datetime.date.today()
    end = datetime.date.today() + datetime.timedelta(days=365)
    equity_narrative = "equity_narrative"
    context = "context"
    gender_narrative = "gender_narrative"
    implementation_strategy = "implementation_strategy"
    ip_program_contribution = "ip_program_contribution"
    sustainability_narrative = "sustainability_narrative"
    # date_sent_to_partner = datetime.date.today()
    risks = factory.RelatedFactory(
        'etools.applications.governments.tests.factories.GDDRiskFactory',
        factory_related_name='gdd'
    )
    capacity_development = "capacity_development"
    other_partners_involved = "other_partners_involved"
    other_details = "other_details"


class GDDAmendmentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.GDDAmendment

    gdd = factory.SubFactory(GDDFactory)
    types = fuzzy.FuzzyChoice([
        ['Change IP name'],
        ['Change authorized officer'],
        ['Change banking info'],
        ['Change in clause'],
    ])
    other_description = fuzzy.FuzzyText(length=50)
    amendment_number = fuzzy.FuzzyInteger(1000)
    signed_date = datetime.date.today()


class GDDAttachmentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.GDDAttachment

    gdd = factory.SubFactory(GDDFactory)
    attachment = factory.django.FileField(filename='test_file.pdf')
    type = factory.SubFactory(FileTypeFactory)


class GDDBudgetFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.GDDBudget
        django_get_or_create = ('gdd',)

    gdd = factory.SubFactory(GDDFactory)
    unicef_cash = 100001.00
    unicef_cash_local = 10.00
    partner_contribution = 200.00
    partner_contribution_local = 20.00
    in_kind_amount = 10.00
    in_kind_amount_local = 10.00


class GDDReviewFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.GDDReview

    gdd = factory.SubFactory(GDDFactory)
    overall_approval = True


class GDDReportingPeriodFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.GDDReportingPeriod

    gdd = factory.SubFactory(GDDFactory)
    # make each period start_date 10 days after the last one
    start_date = factory.Sequence(
        lambda n: datetime.date.today() + datetime.timedelta(days=10 * n)
    )
    # use LazyAttribute to make sure that start_date, end_date
    # and due_date are in order
    end_date = factory.LazyAttribute(
        lambda o: o.start_date + datetime.timedelta(days=3)
    )
    due_date = factory.LazyAttribute(
        lambda o: o.end_date + datetime.timedelta(days=3)
    )


class GDDPlannedVisitsFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.GDDPlannedVisits

    gdd = factory.SubFactory(GDDFactory)
    year = datetime.datetime.today().year


class GDDPlannedVisitSiteFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.GDDPlannedVisitSite

    planned_visit = factory.SubFactory(GDDPlannedVisitsFactory)
    site = factory.SubFactory(LocationSiteFactory)
    quarter = 1


# class AgreementAmendmentFactory(factory.django.DjangoModelFactory):
#
#     class Meta:
#         model = models.AgreementAmendment
#
#     number = factory.Sequence(lambda n: '{:05}'.format(n))
#     types = [models.AgreementAmendment.CLAUSE]


class GDDResultLinkFactory(factory.django.DjangoModelFactory):

    class Meta:
        model = models.GDDResultLink

    gdd = factory.SubFactory(GDDFactory)
    workplan = factory.SubFactory(GovernmentEWPFactory)
    cp_output = factory.SubFactory(EWPOutputFactory)

    @factory.post_generation
    def ram_indicators(self, create, extracted, **kwargs):
        if extracted:
            self.ram_indicators.add(*extracted)


class GDDKeyInterventionFactory(factory.django.DjangoModelFactory):

    class Meta:
        model = models.GDDKeyIntervention

    result_link = factory.SubFactory(GDDResultLinkFactory)
    ewp_key_intervention = factory.SubFactory(EWPKeyInterventionFactory)


class GDDActivityFactory(factory.django.DjangoModelFactory):

    class Meta:
        model = models.GDDActivity

    key_intervention = factory.SubFactory(GDDKeyInterventionFactory)
    ewp_activity = factory.SubFactory(EWPActivityFactory)


# class PlannedEngagementFactory(factory.django.DjangoModelFactory):
#     class Meta:
#         model = models.PlannedEngagement
#
#     partner = factory.SubFactory(PartnerFactory)


class GDDSupplyItemFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.GDDSupplyItem

    gdd = factory.SubFactory(GDDFactory)


class GDDRiskFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.GDDRisk

    gdd = factory.SubFactory(GDDFactory)
    risk_type = fuzzy.FuzzyChoice(choices=dict(models.GDDRisk.RISK_TYPE_CHOICES).keys())
    mitigation_measures = fuzzy.FuzzyText()
