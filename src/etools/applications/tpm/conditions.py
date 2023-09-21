from etools.applications.permissions2.conditions import ModuleCondition, SimpleCondition
from etools.applications.tpm.models import ThirdPartyMonitor


class TPMModuleCondition(ModuleCondition):
    predicate = 'module="tpm"'


class TPMStaffMemberCondition(SimpleCondition):
    predicate = 'user in tpm_tpmpartner.staff_members'

    def __init__(self, organization, user):
        self.organization = organization
        self.user = user

    def is_satisfied(self):
        groups = self.user.get_groups_for_organization_id(self.organization.id, is_active=True)
        return ThirdPartyMonitor.as_group() in groups


class TPMVisitUNICEFFocalPointCondition(SimpleCondition):
    predicate = 'user in tpm_tpmvisit.unicef_focal_points'

    def __init__(self, visit, user):
        self.visit = visit
        self.user = user

    def is_satisfied(self):
        return self.user in self.visit.unicef_focal_points


class TPMVisitTPMFocalPointCondition(SimpleCondition):
    predicate = 'user in tpm_tpmvisit.tpm_partner_focal_points'

    def __init__(self, visit, user):
        self.visit = visit
        self.user = user

    def is_satisfied(self):
        return self.user in self.visit.tpm_partner_focal_points.all()
