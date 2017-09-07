from permissions2.conditions import ModuleCondition, SimpleCondition, BaseRoleCondition


class TPMModuleCondition(ModuleCondition):
    predicate = 'module="tpm"'


class TPMStaffMemberCondition(SimpleCondition):
    predicate = 'user in tpm_tpmpartner.staff_members'

    def __init__(self, partner, user):
        self.partner = partner
        self.user = user

    def is_satisfied(self):
        return self.user.pk in self.partner.staff_members.values_list('user', flat=True)


class TPMVisitUNICEFFocalPointCondition(SimpleCondition):
    predicate = 'user in tpm_tpmvisit.unicef_focal_points'

    def __init__(self, visit, user):
        self.visit = visit
        self.user = user

    def is_satisfied(self):
        return self.user in self.visit.unicef_focal_points.all()


class TPMVisitTPMFocalPointCondition(SimpleCondition):
    predicate = 'user in tpm_tpmvisit.tpm_partner_focal_points'

    def __init__(self, visit, user):
        self.visit = visit
        self.user = user

    def is_satisfied(self):
        return self.user.pk in self.visit.tpm_partner_focal_points.values_list('user', flat=True)


class TPMRoleCondition(BaseRoleCondition):
    user_roles = [
        'PME',
        'Third Party Monitor',
        'UNICEF User',
    ]
