from datetime import timedelta

from django.contrib.auth.models import Group
from django.utils import timezone

import factory.fuzzy

from etools.applications.action_points.models import ActionPoint
from etools.applications.firms.tests.factories import BaseUserFactory
from etools.applications.locations.tests.factories import LocationFactory
from etools.applications.partners.tests.factories import InterventionFactory, ResultFactory
from etools.applications.reports.tests.factories import SectorFactory
from etools.applications.utils.common.tests.factories import InheritedTrait


class UserFactory(BaseUserFactory):
    class Params:
        unicef_user = factory.Trait(
            groups=['UNICEF User'],
        )

        pme = factory.Trait(
            groups=['UNICEF User', 'PME'],
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


class ActionPointFactory(factory.DjangoModelFactory):
    class Meta:
        model = ActionPoint

    intervention = factory.SubFactory(InterventionFactory)
    partner = factory.SelfAttribute('intervention.agreement.partner')
    cp_output = factory.SubFactory(ResultFactory)
    location = factory.SubFactory(LocationFactory)
    description = factory.fuzzy.FuzzyText()
    due_date = factory.fuzzy.FuzzyDate(timezone.now().date() + timedelta(days=1),
                                       timezone.now().date() + timedelta(days=10))

    author = factory.SubFactory(UserFactory)
    assigned_by = factory.SelfAttribute('author')
    section = factory.SubFactory(SectorFactory)
    office = factory.SelfAttribute('author.profile.office')

    assigned_to = factory.SubFactory(UserFactory)

    class Params:
        open = factory.Trait(
            status=ActionPoint.STATUSES.open
        )

        pre_completed = InheritedTrait(
            open,
            action_taken=factory.fuzzy.FuzzyText()
        )

        completed = InheritedTrait(
            pre_completed,
            status=ActionPoint.STATUSES.completed
        )

    @classmethod
    def attributes(cls, create=False, extra=None):
        if extra and 'status' in extra:

            status = extra.pop('status')
            extra[status] = True
        return super(ActionPointFactory, cls).attributes(create, extra)
