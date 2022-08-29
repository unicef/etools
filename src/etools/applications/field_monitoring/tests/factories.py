from django.db import connection

import factory

from etools.applications.audit.models import UNICEFUser
from etools.applications.field_monitoring.groups import FMUser
from etools.applications.firms.tests.factories import BaseUserFactory
from etools.applications.organizations.tests.factories import OrganizationFactory
from etools.applications.tpm.models import PME
from etools.applications.users.tests.factories import GroupFactory, RealmFactory


class UserFactory(BaseUserFactory):
    """
    User factory with ability to quickly assign auditor portal related groups with special logic for auditor.
    """
    class Params:
        unicef_user = factory.Trait(
            realm_set__data=[UNICEFUser.name],
        )

        fm_user = factory.Trait(
            realm_set__data=[UNICEFUser.name, FMUser.name],
        )

        pme = factory.Trait(
            realm_set__data=[UNICEFUser.name, PME.name],
        )

    @factory.post_generation
    def realm_set(self, create, extracted, data=None, **kwargs):
        if not create:
            return

        extracted = (extracted or []) + (data or [])

        if extracted:
            if "UNICEF User" in extracted:
                organization = OrganizationFactory(name='UNICEF', vendor_number='UNICEF')
            else:
                organization = OrganizationFactory()
            for group in extracted:
                if isinstance(group, str):
                    RealmFactory(user=self,
                                 country=connection.get_tenant(),
                                 organization=organization,
                                 group=GroupFactory(name=group))
