
import datetime

import factory
from factory import fuzzy

from etools.applications.partners import models
from etools.applications.reports.tests.factories import CountryProgrammeFactory, ResultFactory, SectionFactory
from etools.applications.users.tests.factories import UserFactory


class WorkspaceFileTypeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.WorkspaceFileType

    name = factory.Sequence(lambda n: 'workspace file type {}'.format(n))


class PartnerStaffFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.PartnerStaffMember

    partner = factory.SubFactory('etools.applications.partners.tests.factories.PartnerFactory')
    title = 'Jedi Master'
    first_name = 'Mace'
    last_name = 'Windu'
    email = factory.Sequence(lambda n: "mace{}@example.com".format(n))


class PartnerFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.PartnerOrganization

    name = factory.Sequence(lambda n: 'Partner {}'.format(n))
    staff_members = factory.RelatedFactory(PartnerStaffFactory, 'partner')


class AgreementFactory(factory.django.DjangoModelFactory):
    '''Factory for Agreements. If the agreement type is PCA (the default), the agreement's end date is set from
    the country_programme so any end date passed to this factory is ignored.
    '''
    class Meta:
        model = models.Agreement

    partner = factory.SubFactory(PartnerFactory)
    agreement_type = 'PCA'
    signed_by_unicef_date = datetime.date.today()
    signed_by_partner_date = datetime.date.today()
    status = 'signed'
    attached_agreement = factory.django.FileField(filename='test_file.pdf')
    country_programme = factory.SubFactory(CountryProgrammeFactory)


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
        'Partnership Review',
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
    signed_amendment = factory.django.FileField(filename='test_file.pdf')


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


class InterventionSectionLocationLinkFactory(factory.django.DjangoModelFactory):

    class Meta:
        model = models.InterventionSectorLocationLink

    intervention = factory.SubFactory(InterventionFactory)
    sector = factory.SubFactory(SectionFactory)


class FundingCommitmentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.FundingCommitment

    grant = factory.SubFactory("etools.applications.funds.tests.factories.GrantFactory")
    fr_number = fuzzy.FuzzyText(length=50)
    wbs = fuzzy.FuzzyText(length=50)
    fc_type = fuzzy.FuzzyText(length=50)


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
