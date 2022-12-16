import random

from django.db.models import signals

import factory
from factory import fuzzy

from etools.applications.audit.models import (
    Audit,
    Auditor,
    DetailedFindingInfo,
    Engagement,
    Finding,
    KeyInternalControl,
    MicroAssessment,
    Risk,
    RiskBluePrint,
    RiskCategory,
    SpecialAudit,
    SpecificProcedure,
    SpotCheck,
    UNICEFAuditFocalPoint,
    UNICEFUser,
)
from etools.applications.audit.purchase_order.models import AuditorFirm, PurchaseOrder, PurchaseOrderItem
from etools.applications.firms.tests.factories import BaseFirmFactory
from etools.applications.partners.models import PartnerOrganization
from etools.applications.partners.tests.factories import AgreementFactory, InterventionFactory, PartnerFactory
from etools.applications.users.tests.factories import CountryFactory, GroupFactory, RealmFactory, UserFactory


class FuzzyBooleanField(fuzzy.BaseFuzzyAttribute):
    def fuzz(self):
        return bool(random.getrandbits(1))


class AgreementWithInterventionsFactory(AgreementFactory):
    interventions = factory.RelatedFactory(InterventionFactory, 'agreement')


class PartnerWithAgreementsFactory(PartnerFactory):
    agreements = factory.RelatedFactory(AgreementWithInterventionsFactory, 'partner')


class AuditFocalPointUserFactory(UserFactory):
    realms__data = [UNICEFUser.name, UNICEFAuditFocalPoint.name]


class AuditorUserFactory(UserFactory):
    realms__data = [Auditor.name]

    @factory.post_generation
    def partner_firm(self, create, extracted, **kwargs):
        if not create:
            return

        if not extracted:
            extracted = AuditPartnerFactory()

        self.profile.organization = extracted.organization
        self.profile.save(update_fields=['organization'])

    @factory.post_generation
    def realms(self, create, extracted, data=None, **kwargs):
        if not create:
            return

        extracted = (extracted or []) + (data or [])
        if extracted:
            organization = self.profile.organization
            for group in extracted:
                if isinstance(group, str):
                    RealmFactory(
                        user=self,
                        country=CountryFactory(),
                        organization=organization,
                        group=GroupFactory(name=group)
                    )

# TODO: REALMS - do cleanup
# class AuditorStaffMemberFactory(BaseStaffMemberFactory):
#     class Meta:
#         model = AuditorStaffMember
#
#     @factory.post_generation
#     def realms(self, create, extracted, **kwargs):
#         if create:
#             RealmFactory(
#                 user=self.user,
#                 country=CountryFactory(),
#                 organization=self.auditor_firm.organization,
#                 group=Auditor.as_group()
#             )


class AuditPartnerFactory(BaseFirmFactory):
    class Meta:
        model = AuditorFirm

    staff_members = factory.RelatedFactory(AuditorUserFactory, 'partner_firm')


class PurchaseOrderItemFactory(factory.django.DjangoModelFactory):
    number = fuzzy.FuzzyInteger(10, 1000, 10)

    class Meta:
        model = PurchaseOrderItem


class PurchaseOrderFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = PurchaseOrder

    auditor_firm = factory.SubFactory(AuditPartnerFactory)
    items = factory.RelatedFactory(PurchaseOrderItemFactory, 'purchase_order')
    order_number = fuzzy.FuzzyText(length=20)


@factory.django.mute_signals(signals.m2m_changed)
class EngagementFactory(factory.django.DjangoModelFactory):
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
        if not create or extracted == []:
            return

        if extracted:
            for member in extracted:
                self.staff_members.add(member)
        else:
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


class StaffSpotCheckFactory(SpotCheckFactory):
    agreement = factory.SubFactory(PurchaseOrderFactory, auditor_firm__unicef_users_allowed=True)


class RiskCategoryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = RiskCategory

    header = factory.Sequence(lambda n: 'category_%d' % n)
    category_type = fuzzy.FuzzyChoice(choices=dict(RiskCategory.TYPES).keys())
    code = fuzzy.FuzzyText(length=20)


class RiskBluePrintFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = RiskBluePrint

    category = factory.SubFactory(RiskCategoryFactory)
    weight = fuzzy.FuzzyInteger(1, 5)
    is_key = FuzzyBooleanField()
    description = fuzzy.FuzzyText(length=30)


class RiskFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Risk

    blueprint = factory.SubFactory(RiskBluePrintFactory)
    engagement = factory.SubFactory(EngagementFactory)

    value = fuzzy.FuzzyChoice(choices=dict(Risk.VALUES).keys())


class FindingFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Finding

    spot_check = factory.SubFactory(SpotCheckFactory)


class KeyInternalControlFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = KeyInternalControl

    audit = factory.SubFactory(SpotCheckFactory)
    recommendation = fuzzy.FuzzyText(length=50).fuzz()
    audit_observation = fuzzy.FuzzyText(length=50).fuzz()
    ip_response = fuzzy.FuzzyText(length=50).fuzz()


class DetailedFindingInfoFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = DetailedFindingInfo

    micro_assesment = factory.SubFactory(MicroAssessmentFactory)
    finding = fuzzy.FuzzyText(length=100)
    recommendation = fuzzy.FuzzyText(length=100)


class SpecificProcedureFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = SpecificProcedure

    audit = factory.SubFactory(SpecialAuditFactory)
    description = fuzzy.FuzzyText(length=100)
    finding = fuzzy.FuzzyText(length=100)
