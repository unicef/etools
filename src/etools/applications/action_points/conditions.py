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
