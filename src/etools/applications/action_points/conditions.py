from etools.applications.permissions2.conditions import ModuleCondition, SimpleCondition


class ActionPointModuleCondition(ModuleCondition):
    predicate = 'module="action_point"'


class ActionPointAuthorCondition(SimpleCondition):
    predicate = 'user=action_points_actionpoint.author'

    def __init__(self, action_point, user):
        self.action_point = action_point
        self.user = user

    def is_satisfied(self):
        return self.user == self.action_point.author


class ActionPointNotAuthorCondition(SimpleCondition):
    predicate = 'user!=action_points_actionpoint.author'

    def __init__(self, action_point, user):
        self.action_point = action_point
        self.user = user

    def is_satisfied(self):
        return self.user != self.action_point.author


class ActionPointAssigneeCondition(SimpleCondition):
    predicate = 'user=action_points_actionpoint.assigned_to'

    def __init__(self, action_point, user):
        self.action_point = action_point
        self.user = user

    def is_satisfied(self):
        return self.user == self.action_point.assigned_to


class ActionPointAssignedByCondition(SimpleCondition):
    predicate = 'user=action_points_actionpoint.assigned_by'

    def __init__(self, action_point, user):
        self.action_point = action_point
        self.user = user

    def is_satisfied(self):
        return self.user == self.action_point.assigned_by


class ActionPointPotentialVerifierCondition(SimpleCondition):
    predicate = 'user=action_points_actionpoint.potential_verifier'

    def __init__(self, action_point, user):
        self.action_point = action_point
        self.user = user

    def is_satisfied(self):
        return self.user == self.action_point.potential_verifier


class RelatedActionPointCondition(SimpleCondition):
    predicate = 'action_points_actionpoint.related_object'

    def __init__(self, action_point):
        self.action_point = action_point

    def is_satisfied(self):
        return self.action_point.related_object is not None


class UnRelatedActionPointCondition(SimpleCondition):
    predicate = '!action_points_actionpoint.related_object'

    def __init__(self, action_point):
        self.action_point = action_point

    def is_satisfied(self):
        return self.action_point.related_object is None


class NotVerifiedActionPointCondition(SimpleCondition):
    predicate = '!action_points_actionpoint.verified'

    def __init__(self, action_point):
        self.action_point = action_point

    def is_satisfied(self):
        return self.action_point.verified_by is None


class PotentialVerifierProvidedCondition(SimpleCondition):
    predicate = 'action_points_actionpoint.potential_verifier_provided'

    def __init__(self, action_point):
        self.action_point = action_point

    def is_satisfied(self):
        return self.action_point.potential_verifier is not None


class HighPriorityActionPointCondition(SimpleCondition):
    predicate = 'action_points_actionpoint.high_priority'

    def __init__(self, action_point):
        self.action_point = action_point

    def is_satisfied(self):
        return self.action_point.high_priority


class LowPriorityActionPointCondition(SimpleCondition):
    predicate = '!action_points_actionpoint.high_priority'

    def __init__(self, action_point):
        self.action_point = action_point

    def is_satisfied(self):
        return not self.action_point.high_priority
