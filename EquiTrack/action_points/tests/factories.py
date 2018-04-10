from __future__ import absolute_import, division, print_function, unicode_literals

from datetime import timedelta

from django.utils import timezone

import factory.fuzzy

from action_points.models import ActionPoint
from locations.tests.factories import LocationFactory
from partners.tests.factories import InterventionFactory, ResultFactory
from reports.tests.factories import SectorFactory
from users.tests.factories import UserFactory


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
        open = factory.Trait()

        completed = factory.Trait(
            status=ActionPoint.STATUSES.completed,
            action_taken=factory.fuzzy.FuzzyText()
        )

    @classmethod
    def attributes(cls, create=False, extra=None):
        if extra and 'status' in extra:
            status = extra.pop('status')
            extra[status] = True
        return super(ActionPointFactory, cls).attributes(create, extra)
