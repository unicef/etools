import random

import factory
from django.contrib.auth.models import Group
from factory import fuzzy

from EquiTrack.factories import PartnerFactory
from audit.models import AuditorFirm, PurchaseOrder, Engagement, RiskCategory, \
    RiskBluePrint, Risk, AuditorStaffMember, MicroAssessment, \
    Audit, SpotCheck, Auditor
from firms.factories import BaseStaffMemberFactory, BaseFirmFactory


class FuzzyBooleanField(fuzzy.BaseFuzzyAttribute):
    def fuzz(self):
        return bool(random.getrandbits(1))


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


class PurchaseOrderFactory(factory.DjangoModelFactory):
    class Meta:
        model = PurchaseOrder

    auditor_firm = factory.SubFactory(AuditPartnerFactory)
    order_number = fuzzy.FuzzyText(length=30)


class EngagementFactory(factory.DjangoModelFactory):
    class Meta:
        model = Engagement

    agreement = factory.SubFactory(PurchaseOrderFactory)
    partner = factory.SubFactory(PartnerFactory)

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
    type = fuzzy.FuzzyChoice(choices=dict(RiskCategory.TYPES).keys())
    code = fuzzy.FuzzyText(length=20)
