import factory
from factory import fuzzy

from etools.applications.comments.models import Comment
from etools.applications.users.tests.factories import UserFactory


class CommentFactory(factory.django.DjangoModelFactory):
    user = factory.SubFactory(UserFactory)
    state = Comment.STATES.active
    instance_related = None
    related_to_description = fuzzy.FuzzyText()
    related_to = fuzzy.FuzzyText(length=10)
    text = fuzzy.FuzzyText(length=50)

    class Meta:
        model = Comment

    @factory.post_generation
    def users_related(self, created, extracted, **kwargs):
        if extracted:
            self.users_related.add(*extracted)
