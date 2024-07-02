from datetime import timedelta

from django.utils import timezone

import factory.fuzzy
from unicef_locations.tests.factories import LocationFactory

from etools.applications.action_points.categories.models import Category
from etools.applications.action_points.models import ActionPoint, ActionPointComment
from etools.applications.partners.tests.factories import InterventionFactory, ResultFactory
from etools.applications.reports.tests.factories import SectionFactory
from etools.applications.users.tests.factories import UserFactory
from etools.libraries.djangolib.utils import get_current_site
from etools.libraries.tests.factories import StatusFactoryMetaClass


class ActionPointCommentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ActionPointComment

    user = factory.SubFactory(UserFactory)
    comment = factory.fuzzy.FuzzyText()
    submit_date = factory.LazyAttribute(lambda o: timezone.now())
    site = factory.LazyAttribute(lambda o: get_current_site())


class ActionPointCategoryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Category

    module = Category.MODULE_CHOICES.apd
    description = factory.fuzzy.FuzzyText()


class BaseActionPointFactory(factory.django.DjangoModelFactory):
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

    author = factory.SubFactory(UserFactory)
    assigned_by = factory.SubFactory(UserFactory)
    section = factory.SubFactory(SectionFactory)
    office = factory.SelfAttribute('author.profile.tenant_profile.office')

    assigned_to = factory.SubFactory(UserFactory)

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
