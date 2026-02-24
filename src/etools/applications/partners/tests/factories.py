import datetime

import factory
from factory import fuzzy
from unicef_locations.tests.factories import LocationFactory

from etools.applications.attachments.tests.factories import AttachmentFactory
from etools.applications.field_monitoring.fm_settings.tests.factories import LocationSiteFactory
from etools.applications.organizations.tests.factories import OrganizationFactory
from etools.applications.partners import models
from etools.applications.partners.models import Intervention, InterventionManagementBudgetItem
from etools.applications.reports.models import ResultType
from etools.applications.reports.tests.factories import (
    CountryProgrammeFactory,
    InterventionActivityFactory,
    LowerResultFactory,
    OfficeFactory,
    ReportingRequirementFactory,
    ResultFactory,
    SectionFactory,
)
from etools.applications.users.tests.factories import UserFactory


class WorkspaceFileTypeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.WorkspaceFileType

    name = factory.Sequence(lambda n: 'workspace file type {}'.format(n))


class PartnerFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.PartnerOrganization

    organization = factory.SubFactory(OrganizationFactory)


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
    accountability_to_affected_populations = "accountability_to_affected_populations"
    other_partners_involved = "other_partners_involved"
    other_details = "other_details"
    cfei_number = "CEF/XXX/2026/001"
    partner_selection_modality = Intervention.SELECTION_MODALITY_OPEN

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


class SignedInterventionFactory(InterventionFactory):
    status = Intervention.SIGNED
    document_type = Intervention.PD
    date_sent_to_partner = datetime.date.today() - datetime.timedelta(days=1)
    signed_by_unicef_date = datetime.date.today() - datetime.timedelta(days=1)
    signed_by_partner_date = datetime.date.today() - datetime.timedelta(days=1)

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        """Create an instance of the model, and save it to the database."""
        if cls._meta.django_get_or_create:
            return cls._get_or_create(model_class, *args, **kwargs)

        manager = cls._get_manager(model_class)
        instance = manager.create(*args, **kwargs)

        instance.flat_locations.add(LocationFactory())
        instance.offices.add(OfficeFactory())
        instance.sections.add(SectionFactory())
        ReportingRequirementFactory(intervention=instance)
        AttachmentFactory(
            code='partners_intervention_signed_pd',
            content_object=instance,
        )
        result_link = InterventionResultLinkFactory(
            intervention=instance,
            cp_output__result_type__name=ResultType.OUTPUT,
        )
        pd_output = LowerResultFactory(result_link=result_link)
        activity = InterventionActivityFactory(result=pd_output)
        activity.time_frames.add(instance.quarters.first())
        return instance

    @factory.post_generation
    def partner_focal_points(self, create, extracted, **kwargs):
        if extracted:
            self.partner_focal_points.add(*extracted)

    @factory.post_generation
    def unicef_focal_points(self, create, extracted, **kwargs):
        if extracted:
            self.unicef_focal_points.add(*extracted)
