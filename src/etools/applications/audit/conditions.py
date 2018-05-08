from etools.applications.permissions2.conditions import ModuleCondition, SimpleCondition


class AuditModuleCondition(ModuleCondition):
    predicate = 'module="audit"'


class AuditStaffMemberCondition(SimpleCondition):
    predicate = 'user in audit_auditorfirm.staff_members'

    def __init__(self, partner, user):
        self.partner = partner
        self.user = user

    def is_satisfied(self):
        return self.user.pk in self.partner.staff_members.values_list('user', flat=True)
