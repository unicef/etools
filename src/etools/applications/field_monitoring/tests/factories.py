from django.contrib.auth.models import Group

import factory
from factory import fuzzy

from etools.applications.field_monitoring.models import MethodType, UNICEFUser
from etools.applications.field_monitoring_shared.models import Method
from etools.applications.firms.tests.factories import BaseUserFactory


class UserFactory(BaseUserFactory):
    """
    User factory with ability to quickly assign auditor portal related groups with special logic for auditor.
    """
    class Params:
        unicef_user = factory.Trait(
            groups=[UNICEFUser.name],
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


class MethodFactory(factory.DjangoModelFactory):
    name = fuzzy.FuzzyText()

    class Meta:
        model = Method


class MethodTypeFactory(factory.DjangoModelFactory):
    method = factory.SubFactory(MethodFactory, is_types_applicable=True)
    name = fuzzy.FuzzyText()

    class Meta:
        model = MethodType
