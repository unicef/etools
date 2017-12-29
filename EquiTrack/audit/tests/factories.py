from __future__ import absolute_import, division, print_function, unicode_literals

import datetime
import random

from django.contrib.auth.models import Group

import factory
from factory import fuzzy

from audit.models import (
    Audit,
    Auditor,
    AuditorFirm,
    AuditPermission,
    AuditorStaffMember,
    DetailedFindingInfo,
    Engagement,
    EngagementActionPoint,
    Finding,
    MicroAssessment,
    PurchaseOrder,
    PurchaseOrderItem,
    Risk,
    RiskBluePrint,
    RiskCategory,
    SpecialAudit,
    SpotCheck,
)
from firms.tests.factories import BaseFirmFactory, BaseStaffMemberFactory
from partners.tests.factories import (
    AgreementFactory,
    InterventionFactory,
    PartnerFactory,
)


class FuzzyBooleanField(fuzzy.BaseFuzzyAttribute):
    def fuzz(self):
        return bool(random.getrandbits(1))


class AgreementWithInterventionsFactory(AgreementFactory):
    interventions = factory.RelatedFactory(InterventionFactory, 'agreement')


class PartnerWithAgreementsFactory(PartnerFactory):
    agreements = factory.RelatedFactory(AgreementWithInterventionsFactory, 'partner')


class AuditorStaffMemberFactory(BaseStaffMemberFactory):
    class Meta:
        model = AuditorStaffMember

    @factory.post_generation
    def user_groups(self, create, extracted, **kwargs):
        if create:
            self.user.groups = [
                Group.objects.get_or_create(name=Auditor.name)[0]
            ]


class AuditPartnerFactory(BaseFirmFactory):
    class Meta:
        model = AuditorFirm

    staff_members = factory.RelatedFactory(AuditorStaffMemberFactory, 'auditor_firm')


class PurchaseOrderItemFactory(factory.DjangoModelFactory):
    number = fuzzy.FuzzyInteger(10, 1000, 10)

    class Meta:
        model = PurchaseOrderItem


class PurchaseOrderFactory(factory.DjangoModelFactory):
    class Meta:
        model = PurchaseOrder

    auditor_firm = factory.SubFactory(AuditPartnerFactory)
    items = factory.RelatedFactory(PurchaseOrderItemFactory, 'purchase_order')


class EngagementFactory(factory.DjangoModelFactory):
    class Meta:
        model = Engagement

    agreement = factory.SubFactory(PurchaseOrderFactory)
    partner = factory.SubFactory(PartnerWithAgreementsFactory)

    @factory.post_generation
    def active_pd(self, create, extracted, **kwargs):
        if create:
            self.active_pd.add(*self.partner.agreements.first().interventions.all())

    @factory.post_generation
    def staff_members(self, create, extracted, **kwargs):
        if create:
            self.staff_members.add(*self.agreement.auditor_firm.staff_members.all())


class MicroAssessmentFactory(EngagementFactory):
    class Meta:
        model = MicroAssessment


class AuditFactory(EngagementFactory):
    class Meta:
        model = Audit


class SpecialAuditFactory(EngagementFactory):
    class Meta:
        model = SpecialAudit


class SpotCheckFactory(EngagementFactory):
    class Meta:
        model = SpotCheck


class RiskFactory(factory.DjangoModelFactory):
    class Meta:
        model = Risk

    value = fuzzy.FuzzyChoice(choices=dict(Risk.VALUES).keys())


class RiskBluePrintFactory(factory.DjangoModelFactory):
    class Meta:
        model = RiskBluePrint

    weight = fuzzy.FuzzyInteger(1, 5)
    is_key = FuzzyBooleanField()
    description = fuzzy.FuzzyText(length=30)


class RiskCategoryFactory(factory.DjangoModelFactory):
    class Meta:
        model = RiskCategory

    header = factory.Sequence(lambda n: 'category_%d' % n)
    category_type = fuzzy.FuzzyChoice(choices=dict(RiskCategory.TYPES).keys())
    code = fuzzy.FuzzyText(length=20)


class FindingFactory(factory.DjangoModelFactory):
    class Meta:
        model = Finding

    spot_check = factory.SubFactory(SpotCheckFactory)


class DetailedFindingInfoFactory(factory.DjangoModelFactory):
    class Meta:
        model = DetailedFindingInfo

    micro_assesment = factory.SubFactory(MicroAssessmentFactory)
    finding = fuzzy.FuzzyText(length=100)
    recommendation = fuzzy.FuzzyText(length=100)


class EngagementActionPointFactory(factory.DjangoModelFactory):
    class Meta:
        model = EngagementActionPoint

    description = fuzzy.FuzzyText(length=100)
    due_date = fuzzy.FuzzyDate(datetime.date(2001, 1, 1))


class AuditPermissionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = AuditPermission

    user_type = fuzzy.FuzzyChoice(AuditPermission.USER_TYPES)
    permission = fuzzy.FuzzyChoice(AuditPermission.PERMISSIONS)
    permission_type = fuzzy.FuzzyChoice(AuditPermission.TYPES)
    target = fuzzy.FuzzyText(length=100)
    instance_status = fuzzy.FuzzyChoice(AuditPermission.STATUSES)
