from datetime import timedelta

from django.contrib.auth.models import Group
from django.utils import timezone

import factory.fuzzy
from django_comments.models import Comment

from etools.applications.EquiTrack.utils import get_current_site
from etools.applications.action_points.models import ActionPoint
from etools.applications.action_points.categories.models import Category
from etools.applications.firms.tests.factories import BaseUserFactory
from unicef_locations.tests.factories import LocationFactory
from etools.applications.partners.tests.factories import InterventionFactory, ResultFactory
from etools.applications.reports.tests.factories import SectionFactory
from etools.applications.utils.common.tests.factories import StatusFactoryMetaClass


class UserFactory(BaseUserFactory):
    """
    User factory with ability to quickly assign action points module-related groups.
    """
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


class ActionPointCommentFactory(factory.DjangoModelFactory):
    class Meta:
        model = Comment

    user = factory.SubFactory(UserFactory, unicef_user=True)
    comment = factory.fuzzy.FuzzyText()
    submit_date = factory.LazyAttribute(lambda o: timezone.now())
    site = factory.LazyAttribute(lambda o: get_current_site())


class ActionPointCategoryFactory(factory.DjangoModelFactory):
    class Meta:
        model = Category

    module = Category.MODULE_CHOICES.apd
    description = factory.fuzzy.FuzzyText()


class BaseActionPointFactory(factory.DjangoModelFactory):
    class Meta:
        model = ActionPoint

    intervention = factory.SubFactory(InterventionFactory)
    partner = factory.SelfAttribute('intervention.agreement.partner')
    cp_output = factory.SubFactory(ResultFactory)
    location = factory.SubFactory(LocationFactory)
    category = factory.SubFactory(ActionPointCategoryFactory)
    description = factory.fuzzy.FuzzyText()
    due_date = factory.fuzzy.FuzzyDate(timezone.now().date() + timedelta(days=1),
                                       timezone.now().date() + timedelta(days=10))

    author = factory.SubFactory(UserFactory, unicef_user=True)
    assigned_by = factory.SubFactory(UserFactory, unicef_user=True)
    section = factory.SubFactory(SectionFactory)
    office = factory.SelfAttribute('author.profile.office')

    assigned_to = factory.SubFactory(UserFactory, unicef_user=True)

    @factory.post_generation
    def comments(self, create, extracted, count=0, **kwargs):
        if not create:
            return

        for i in range(count):
            ActionPointCommentFactory(content_object=self, **kwargs)


class OpenActionPointFactory(BaseActionPointFactory):
    status = ActionPoint.STATUSES.open


class PreCompletedActionPointFactory(OpenActionPointFactory):
    comments__count = 3


class CompletedActionPointFactory(PreCompletedActionPointFactory):
    status = ActionPoint.STATUSES.completed


class ActionPointFactory(BaseActionPointFactory, metaclass=StatusFactoryMetaClass):
    status_factories = {
        'open': OpenActionPointFactory,
        'pre_completed': PreCompletedActionPointFactory,
        'completed': CompletedActionPointFactory,
    }
