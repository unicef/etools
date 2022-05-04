from etools.applications.permissions2.conditions import ModuleCondition, SimpleCondition


class AuditModuleCondition(ModuleCondition):
    predicate = 'module="audit"'


class AuditStaffMemberCondition(SimpleCondition):
    predicate = 'user in audit_auditorfirm.staff_members'

    def __init__(self, partner, user):
        self.partner = partner
        self.user = user

    def is_satisfied(self):
        return self.partner.staff_members.exists() and self.user.pk in self.partner.staff_members.values_list(
            'user', flat=True)


class EngagementStaffMemberCondition(SimpleCondition):
    predicate = 'user in audit_engagement.staff_members'

    def __init__(self, engagement, user):
        self.engagement = engagement
        self.user = user

    def is_satisfied(self):
        return hasattr(self.user, 'purchase_order_auditorstaffmember'
                       ) and self.user.purchase_order_auditorstaffmember in self.engagement.staff_members.all()


class IsStaffMemberCondition(SimpleCondition):
    predicate = 'user.is_staff'

    def __init__(self, user):
        self.user = user

    def is_satisfied(self):
        return self.user.is_staff
