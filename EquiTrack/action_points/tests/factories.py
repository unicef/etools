from datetime import timedelta

import factory.fuzzy
from django.utils import timezone

from EquiTrack.factories import InterventionFactory, ResultFactory, LocationFactory, UserFactory
from action_points.models import ActionPoint


class ActionPointFactory(factory.DjangoModelFactory):
    class Meta:
        model = ActionPoint

    related_module = factory.fuzzy.FuzzyChoice(dict(ActionPoint.MODULE_CHOICES).keys())
    intervention = factory.SubFactory(InterventionFactory)
    partner = factory.SelfAttribute('intervention.agreement.partner')
    cp_output = factory.SubFactory(ResultFactory)
    location = factory.SubFactory(LocationFactory)
    description = factory.fuzzy.FuzzyText()
    due_date = factory.fuzzy.FuzzyDate(timezone.now() + timedelta(days=1))

    author = factory.SubFactory(UserFactory)
    section = factory.SelfAttribute('author.profile.section')
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
