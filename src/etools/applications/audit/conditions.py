from etools.applications.audit.models import Auditor
from etools.applications.permissions2.conditions import ModuleCondition, SimpleCondition


class AuditModuleCondition(ModuleCondition):
    predicate = 'module="audit"'


class AuditStaffMemberCondition(SimpleCondition):
    predicate = 'user in audit_auditorfirm.staff_members'

    def __init__(self, organization, user):
        self.organization = organization
        self.user = user

    def is_satisfied(self):
        return Auditor.as_group() in self.user.get_groups_for_organization_id(self.organization.id, is_active=True)


class EngagementStaffMemberCondition(SimpleCondition):
    predicate = 'user in audit_engagement.staff_members'

    def __init__(self, engagement, user):
        self.engagement = engagement
        self.user = user

    def is_satisfied(self):
        return self.user in self.engagement.staff_members.all()


class IsUnicefUserCondition(SimpleCondition):
    predicate = 'user.is_unicef_user'

    def __init__(self, user):
        self.user = user

    def is_satisfied(self):
        return self.user.is_unicef_user()


class EngagementUnicefCommentsReceivedCondition(SimpleCondition):
    predicate = 'audit_engagement.date_of_comments_by_unicef'

    def __init__(self, engagement):
        self.engagement = engagement

    def is_satisfied(self):
        return self.engagement.date_of_comments_by_unicef is not None
