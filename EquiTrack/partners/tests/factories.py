from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import datetime

import factory
from factory import fuzzy

from EquiTrack.factories import (
    CountryProgrammeFactory,
    ResultFactory,
    SectorFactory,
    UserFactory,
)
from partners import models


class WorkspaceFileTypeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.WorkspaceFileType

    name = factory.Sequence(lambda n: 'workspace file type {}'.format(n))


class PartnerStaffFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.PartnerStaffMember

    partner = factory.SubFactory('partners.tests.factories.PartnerFactory')
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
    agreement_type = u'PCA'
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
        u'Micro Assessment',
        u'Simplified Checklist',
        u'Scheduled Audit report',
        u'Special Audit report',
        u'Other',
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

    name = fuzzy.FuzzyChoice([
        u'FACE',
        u'Progress Report',
        u'Partnership Review',
        u'Final Partnership Review',
        u'Correspondence',
        u'Supply/Distribution Plan',
        u'Other',
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
        [u'Change IP name'],
        [u'Change authorized officer'],
        [u'Change banking info'],
        [u'Change in clause'],
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
    type = factory.Iterator(models.FileType.objects.all())


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
    programmatic = 1
    spot_checks = 2
    audit = 3


class GovernmentInterventionFactory(factory.DjangoModelFactory):
    class Meta:
        model = models.GovernmentIntervention

    partner = factory.SubFactory(PartnerFactory)
    country_programme = factory.SubFactory(CountryProgrammeFactory)
    number = 'RefNumber'


class GovernmentInterventionResultFactory(factory.django.DjangoModelFactory):

    class Meta:
        model = models.GovernmentInterventionResult

    intervention = factory.SubFactory(GovernmentInterventionFactory)
    result = factory.SubFactory(ResultFactory)
    year = '2017'


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


class InterventionSectorLocationLinkFactory(factory.django.DjangoModelFactory):

    class Meta:
        model = models.InterventionSectorLocationLink

    intervention = factory.SubFactory(InterventionFactory)
    sector = factory.SubFactory(SectorFactory)


class FundingCommitmentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.FundingCommitment

    grant = factory.SubFactory("funds.tests.factories.GrantFactory")
    fr_number = fuzzy.FuzzyText(length=50)
    wbs = fuzzy.FuzzyText(length=50)
    fc_type = fuzzy.FuzzyText(length=50)
