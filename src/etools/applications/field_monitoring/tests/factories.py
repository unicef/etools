from django.contrib.auth.models import Group

import factory

from etools.applications.field_monitoring.groups import UNICEFUser, FMUser, PME
from etools.applications.firms.tests.factories import BaseUserFactory


class UserFactory(BaseUserFactory):
    """
    User factory with ability to quickly assign auditor portal related groups with special logic for auditor.
    """
    class Params:
        unicef_user = factory.Trait(
            groups=[UNICEFUser.name],
        )

        fm_user = factory.Trait(
            groups=[UNICEFUser.name, FMUser.name],
        )

        pme = factory.Trait(
            groups=[UNICEFUser.name, PME.name],
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
