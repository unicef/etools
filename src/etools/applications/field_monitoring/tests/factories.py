import factory

from etools.applications.audit.models import UNICEFUser
from etools.applications.field_monitoring.groups import FMUser, MonitoringVisitApprover, ReportReviewer
from etools.applications.firms.tests.factories import BaseUserFactory
from etools.applications.organizations.tests.factories import OrganizationFactory
from etools.applications.tpm.models import PME
from etools.applications.users.tests.factories import CountryFactory, GroupFactory, RealmFactory


class UserFactory(BaseUserFactory):
    """
    User factory with ability to quickly assign auditor portal related groups with special logic for auditor.
    """
    class Params:
        unicef_user = factory.Trait(
            realms__data=[UNICEFUser.name],
        )

        fm_user = factory.Trait(
            realms__data=[UNICEFUser.name, FMUser.name],
        )

        pme = factory.Trait(
            realms__data=[UNICEFUser.name, PME.name],
        )

        approver = factory.Trait(
            realms__data=[UNICEFUser.name, MonitoringVisitApprover.name],
        )

        report_reviewer = factory.Trait(
            realms__data=[UNICEFUser.name, ReportReviewer.name]
        )

    @factory.post_generation
    def realms(self, create, extracted, data=None, **kwargs):
        if not create:
            return

        extracted = (extracted or []) + (data or [])

        if extracted:
            if "UNICEF User" in extracted:
                organization = OrganizationFactory(name='UNICEF', vendor_number='000')
                if hasattr(self, 'profile') and self.profile:
                    self.profile.organization = organization
                    self.profile.save(update_fields=['organization'])
            else:
                organization = self.profile.organization
            for group in extracted:
                if isinstance(group, str):
                    RealmFactory(user=self,
                                 country=CountryFactory(),
                                 organization=organization,
                                 group=GroupFactory(name=group))
