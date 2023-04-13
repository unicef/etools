import datetime

import factory
from factory import fuzzy

from etools.applications.attachments.tests.factories import AttachmentFactory
from etools.applications.field_monitoring.fm_settings.tests.factories import LocationSiteFactory
from etools.applications.partners import models
from etools.applications.partners.models import InterventionManagementBudgetItem
from etools.applications.reports.tests.factories import CountryProgrammeFactory, ResultFactory
from etools.applications.users.tests.factories import UserFactory


class WorkspaceFileTypeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.WorkspaceFileType

    name = factory.Sequence(lambda n: 'workspace file type {}'.format(n))


class PartnerStaffFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.PartnerStaffMember

    user = factory.SubFactory(UserFactory, groups__data=[], is_staff=False)
    partner = factory.SubFactory('etools.applications.partners.tests.factories.PartnerFactory')
    title = 'Jedi Master'
    first_name = 'Mace'
    last_name = 'Windu'
    email = factory.SelfAttribute('user.email')


class PartnerFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.PartnerOrganization

    name = factory.Sequence(lambda n: 'Partner {}'.format(n))
    staff_members = factory.RelatedFactory(PartnerStaffFactory, 'partner')


class CoreValuesAssessmentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.CoreValuesAssessment

    partner = factory.SubFactory(PartnerFactory)


class AgreementFactory(factory.django.DjangoModelFactory):
    """Factory for Agreements. If the agreement type is PCA (the default), the agreement's end date is set from
    the country_programme so any end date passed to this factory is ignored.
    """
    class Meta:
        model = models.Agreement

    partner = factory.SubFactory(PartnerFactory)
    agreement_type = 'PCA'
    signed_by_unicef_date = datetime.date.today()
    signed_by_partner_date = datetime.date.today()
    status = 'signed'
    reference_number_year = datetime.date.today().year
    country_programme = factory.SubFactory(CountryProgrammeFactory)

    @factory.post_generation
    def attachment(self, create, extracted, **kwargs):
        if not create:
            return
        AttachmentFactory(code='partners_agreement', content_object=self)


class AssessmentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.Assessment

    partner = factory.SubFactory(PartnerFactory)
    type = fuzzy.FuzzyChoice([
        'Micro Assessment',
        'Simplified Checklist',
        'Scheduled Audit report',
        'Special Audit report',
        'Other',
    ])
    names_of_other_agencies = fuzzy.FuzzyText(length=50)
    expected_budget = fuzzy.FuzzyInteger(1000)
    notes = fuzzy.FuzzyText(length=50)
    requested_date = datetime.date.today()
    requesting_officer = factory.SubFactory(UserFactory)
    approving_officer = factory.SubFactory(UserFactory)
    planned_date = datetime.date.today()
    completed_date = datetime.date.today()
    rating = "high"
    report = factory.django.FileField(filename='test_file.pdf')
    current = True


class FileTypeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.FileType
        django_get_or_create = ("name", )

    name = fuzzy.FuzzyChoice([
        'FACE',
        'Progress Report',
        'Final Partnership Review',
        'Correspondence',
        'Supply/Distribution Plan',
        'Other',
    ])


class InterventionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.Intervention

    agreement = factory.SubFactory(AgreementFactory)
    title = factory.Sequence(lambda n: 'Intervention Title {}'.format(n))
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
        'etools.applications.partners.tests.factories.InterventionRiskFactory',
        factory_related_name='intervention'
    )
    capacity_development = "capacity_development"
    other_partners_involved = "other_partners_involved"
    other_details = "other_details"

    @factory.post_generation
    def country_programmes(self, create, extracted, **kwargs):
        if create and self.country_programme:
            self.country_programmes.add(self.country_programme)

        if extracted:
            self.country_programmes.add(*extracted)


class InterventionAmendmentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.InterventionAmendment

    intervention = factory.SubFactory(InterventionFactory)
    types = fuzzy.FuzzyChoice([
        ['Change IP name'],
        ['Change authorized officer'],
        ['Change banking info'],
        ['Change in clause'],
    ])
    other_description = fuzzy.FuzzyText(length=50)
    amendment_number = fuzzy.FuzzyInteger(1000)
    signed_date = datetime.date.today()


class InterventionAttachmentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.InterventionAttachment

    intervention = factory.SubFactory(InterventionFactory)
    attachment = factory.django.FileField(filename='test_file.pdf')
    type = factory.SubFactory(FileTypeFactory)


class InterventionBudgetFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.InterventionBudget

    intervention = factory.SubFactory(InterventionFactory)
    unicef_cash = 100001.00
    unicef_cash_local = 10.00
    partner_contribution = 200.00
    partner_contribution_local = 20.00
    in_kind_amount = 10.00
    in_kind_amount_local = 10.00


class InterventionReviewFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.InterventionReview

    intervention = factory.SubFactory(InterventionFactory)
    overall_approval = True


class InterventionReportingPeriodFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.InterventionReportingPeriod

    intervention = factory.SubFactory(InterventionFactory)
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


class InterventionPlannedVisitsFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.InterventionPlannedVisits

    intervention = factory.SubFactory(InterventionFactory)
    year = datetime.datetime.today().year


class InterventionPlannedVisitSiteFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.InterventionPlannedVisitSite

    planned_visit = factory.SubFactory(InterventionPlannedVisitsFactory)
    site = factory.SubFactory(LocationSiteFactory)
    quarter = 1


class AgreementAmendmentFactory(factory.django.DjangoModelFactory):

    class Meta:
        model = models.AgreementAmendment

    number = factory.Sequence(lambda n: '{:05}'.format(n))
    agreement = factory.SubFactory(AgreementFactory)
    types = [models.AgreementAmendment.CLAUSE]


class InterventionResultLinkFactory(factory.django.DjangoModelFactory):

    class Meta:
        model = models.InterventionResultLink

    intervention = factory.SubFactory(InterventionFactory)
    cp_output = factory.SubFactory(ResultFactory)

    @factory.post_generation
    def ram_indicators(self, create, extracted, **kwargs):
        if extracted:
            self.ram_indicators.add(*extracted)


class PlannedEngagementFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.PlannedEngagement

    partner = factory.SubFactory(PartnerFactory)


class PartnerPlannedVisitsFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.PartnerPlannedVisits
        django_get_or_create = ("partner", "year")

    partner = factory.SubFactory(PartnerFactory)
    year = datetime.date.today().year


class InterventionManagementBudgetFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.InterventionManagementBudget
        django_get_or_create = ("intervention",)

    intervention = factory.SubFactory(InterventionFactory)


class InterventionSupplyItemFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.InterventionSupplyItem

    intervention = factory.SubFactory(InterventionFactory)


class InterventionRiskFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.InterventionRisk

    intervention = factory.SubFactory(InterventionFactory)
    risk_type = fuzzy.FuzzyChoice(choices=dict(models.InterventionRisk.RISK_TYPE_CHOICES).keys())
    mitigation_measures = fuzzy.FuzzyText()


class InterventionManagementBudgetItemFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.InterventionManagementBudgetItem

    budget = factory.SubFactory(InterventionManagementBudgetFactory)
    name = factory.fuzzy.FuzzyText(length=100)
    kind = factory.fuzzy.FuzzyChoice(dict(InterventionManagementBudgetItem.KIND_CHOICES).keys())
    unit = factory.fuzzy.FuzzyText()
    unit_price = factory.fuzzy.FuzzyDecimal(1)
    no_units = factory.fuzzy.FuzzyDecimal(0.1)
