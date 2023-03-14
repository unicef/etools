import factory
from post_office.models import Email


class EmailFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Email

    from_email = factory.Sequence(lambda n: "mace{}@example.com".format(n))
