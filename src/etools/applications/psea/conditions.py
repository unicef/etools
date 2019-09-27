from etools.applications.permissions2.conditions import ModuleCondition, SimpleCondition


class PSEAModuleCondition(ModuleCondition):
    predicate = 'module="psea"'


class PSEAUNICEFFocalPointCondition(SimpleCondition):
    predicate = 'user in assessment.focal_points'

    def __init__(self, assessment, user):
        self.assessment = assessment
        self.user = user

    def is_satisfied(self):
        return self.user in self.assessment.focal_points
