
import datetime
import random

from django.contrib.auth.models import Group

import factory
from factory import fuzzy

from etools.applications.audit.models import (Audit, Auditor, DetailedFindingInfo, Engagement,
                                              EngagementActionPoint, Finding, KeyInternalControl, MicroAssessment,
                                              Risk, RiskBluePrint, RiskCategory, SpecialAudit, SpecificProcedure,
                                              SpotCheck, UNICEFAuditFocalPoint, UNICEFUser,)
from etools.applications.audit.purchase_order.models import (AuditorFirm, AuditorStaffMember,
                                                             PurchaseOrder, PurchaseOrderItem,)
from etools.applications.firms.tests.factories import BaseFirmFactory, BaseStaffMemberFactory
from etools.applications.partners.models import PartnerOrganization
from etools.applications.partners.tests.factories import AgreementFactory, InterventionFactory, PartnerFactory
from etools.applications.users.tests.factories import UserFactory as BaseUserFactory


class FuzzyBooleanField(fuzzy.BaseFuzzyAttribute):
    def fuzz(self):
        return bool(random.getrandbits(1))


class AgreementWithInterventionsFactory(AgreementFactory):
    interventions = factory.RelatedFactory(InterventionFactory, 'agreement')


class PartnerWithAgreementsFactory(PartnerFactory):
    agreements = factory.RelatedFactory(AgreementWithInterventionsFactory, 'partner')


class UserFactory(BaseUserFactory):
    class Params:
        unicef_user = factory.Trait(
            groups=[UNICEFUser.name],
        )

        audit_focal_point = factory.Trait(
            groups=[UNICEFUser.name, UNICEFAuditFocalPoint.name],
        )

        auditor = factory.Trait(
            groups=[Auditor.name],
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

    @factory.post_generation
    def partner_firm(self, create, extracted, **kwargs):
        if not create:
            return

        if Auditor.name not in self.groups.values_list('name', flat=True):
            return

        if not extracted:
            extracted = AuditPartnerFactory()

        AuditorStaffMemberFactory(auditor_firm=extracted, user=self)


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
    order_number = fuzzy.FuzzyText(length=20)


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
