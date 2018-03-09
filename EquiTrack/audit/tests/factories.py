from __future__ import absolute_import, division, print_function, unicode_literals

import datetime
import random

from django.contrib.auth.models import Group

import factory
from factory import fuzzy

from audit.models import (
    Audit,
    Auditor,
    AuditPermission,
    DetailedFindingInfo,
    Engagement,
    EngagementActionPoint,
    Finding,
    MicroAssessment,
    Risk,
    RiskBluePrint,
    RiskCategory,
    SpecialAudit,
    SpotCheck,
    SpecificProcedure,
    KeyInternalControl)
from audit.purchase_order.models import AuditorFirm, AuditorStaffMember, PurchaseOrder, PurchaseOrderItem
from EquiTrack.factories import (
    AgreementFactory,
    InterventionFactory,
    PartnerFactory,
)
from firms.factories import BaseFirmFactory, BaseStaffMemberFactory
from partners.models import PartnerOrganization


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
    shared_ip_with = list(map(lambda c: c[0], PartnerOrganization.AGENCY_CHOICES))

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


class RiskCategoryFactory(factory.DjangoModelFactory):
    class Meta:
        model = RiskCategory

    header = factory.Sequence(lambda n: 'category_%d' % n)
    category_type = fuzzy.FuzzyChoice(choices=dict(RiskCategory.TYPES).keys())
    code = fuzzy.FuzzyText(length=20)


class RiskBluePrintFactory(factory.DjangoModelFactory):
    class Meta:
        model = RiskBluePrint

    category = factory.SubFactory(RiskCategoryFactory)
    weight = fuzzy.FuzzyInteger(1, 5)
    is_key = FuzzyBooleanField()
    description = fuzzy.FuzzyText(length=30)


class RiskFactory(factory.DjangoModelFactory):
    class Meta:
        model = Risk

    blueprint = factory.SubFactory(RiskBluePrintFactory)
    engagement = factory.SubFactory(EngagementFactory)

    value = fuzzy.FuzzyChoice(choices=dict(Risk.VALUES).keys())


class FindingFactory(factory.DjangoModelFactory):
    class Meta:
        model = Finding

    spot_check = factory.SubFactory(SpotCheckFactory)


class KeyInternalControlFactory(factory.DjangoModelFactory):
    class Meta:
        model = KeyInternalControl

    audit = factory.SubFactory(SpotCheckFactory)
    recommendation = fuzzy.FuzzyText(length=50).fuzz()
    audit_observation = fuzzy.FuzzyText(length=50).fuzz()
    ip_response = fuzzy.FuzzyText(length=50).fuzz()


class DetailedFindingInfoFactory(factory.DjangoModelFactory):
    class Meta:
        model = DetailedFindingInfo

    micro_assesment = factory.SubFactory(MicroAssessmentFactory)
    finding = fuzzy.FuzzyText(length=100)
    recommendation = fuzzy.FuzzyText(length=100)


class SpecificProcedureFactory(factory.DjangoModelFactory):
    class Meta:
        model = SpecificProcedure

    audit = factory.SubFactory(SpecialAuditFactory)
    description = fuzzy.FuzzyText(length=100)
    finding = fuzzy.FuzzyText(length=100)


class EngagementActionPointFactory(factory.DjangoModelFactory):
    class Meta:
        model = EngagementActionPoint

    category = fuzzy.FuzzyChoice(EngagementActionPoint.CATEGORY_CHOICES)
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
