from django.core.management import BaseCommand
from django.db.models import Q

from etools.applications.action_points.conditions import (
    ActionPointAssignedByCondition,
    ActionPointAssigneeCondition,
    ActionPointAuthorCondition,
)
from etools.applications.action_points.models import ActionPoint
from etools.applications.audit.conditions import AuditStaffMemberCondition
from etools.applications.audit.models import Auditor, UNICEFAuditFocalPoint, UNICEFUser
from etools.applications.permissions2.conditions import GroupCondition, NewObjectCondition, ObjectStatusCondition
from etools.applications.permissions2.models import Permission
from etools.applications.permissions2.utils import get_model_target
from etools.applications.psea.conditions import PSEAModuleCondition
from etools.applications.psea.models import Assessment, AssessmentActionPoint


class Command(BaseCommand):
    action_points_block = [
        'psea.assessment.action_points',
        'psea.assessmentactionpoint.*',
    ]

    follow_up_editable_page = ['psea.assessment']
    follow_up_page = follow_up_editable_page + action_points_block

    focal_point = 'focal_point'
    unicef_user = 'unicef_user'
    auditor = 'auditor'

    all_unicef_users = [focal_point, unicef_user]
    everybody = all_unicef_users + [auditor, ]

    action_point_author = 'action_point_author'
    action_point_assignee = 'action_point_assignee'
    action_point_assigned_by = 'action_point_assigned_by'
    action_points_editors = [
        focal_point,
        action_point_author,
        action_point_assignee,
        action_point_assigned_by,
    ]

    user_roles = {
        focal_point: [
            GroupCondition.predicate_template.format(
                group=UNICEFAuditFocalPoint.name,
            ),
        ],
        unicef_user: [
            GroupCondition.predicate_template.format(group=UNICEFUser.name),
        ],
        auditor: [
            GroupCondition.predicate_template.format(group=Auditor.name),
            AuditStaffMemberCondition.predicate,
        ],

        action_point_author: [ActionPointAuthorCondition.predicate],
        action_point_assignee: [ActionPointAssigneeCondition.predicate],
        action_point_assigned_by: [ActionPointAssignedByCondition.predicate],
    }

    def _update_permissions(self, role, perm, targets, perm_type, condition=None):
        if isinstance(role, (list, tuple)):
            for r in role:
                self._update_permissions(r, perm, targets, perm_type, condition)
            return

        if isinstance(targets, str):
            targets = [targets]

        condition = (condition or []) + [PSEAModuleCondition()] + self.user_roles[role]

        if self.verbosity >= 3:
            for target in targets:
                print(
                    '   {} {} permission for {} on {}\n'
                    '      if {}.'.format(
                        'Add' if perm_type == 'allow' else 'Revoke',
                        perm,
                        role,
                        target,
                        condition,
                    )
                )

        self.defined_permissions.extend([
            Permission(
                target=target,
                permission=perm,
                permission_type=perm_type,
                condition=condition,
            )
            for target in targets
        ])

    def add_permissions(self, role, perm, targets, condition=None):
        self._update_permissions(role, perm, targets, 'allow', condition)

    def revoke_permissions(self, role, perm, targets, condition=None):
        self._update_permissions(role, perm, targets, 'disallow', condition)

    def assessment_status(self, status):
        obj = get_model_target(Assessment)
        return [
            ObjectStatusCondition.predicate_template.format(
                obj=obj,
                status=status,
            ),
        ]

    def new_action_point(self):
        model = get_model_target(AssessmentActionPoint)
        return [NewObjectCondition.predicate_template.format(model=model)]

    def action_point_status(self, status):
        # root status class should be used here for proper condition work
        obj = get_model_target(ActionPoint)
        return [
            ObjectStatusCondition.predicate_template.format(
                obj=obj,
                status=status,
            ),
        ]

    def handle(self, *args, **options):
        self.verbosity = options.get('verbosity', 1)

        self.defined_permissions = []

        if self.verbosity >= 2:
            print(
                'Generating new permissions...'
            )

        self.assign_permissions()

        old_permissions = Permission.objects.filter(
            Q(target__startswith='psea.')
        )
        old_permissions_count = old_permissions.count()

        if self.verbosity >= 2:
            self.stdout.write(
                'Deleting old permissions...'
            )
        old_permissions.delete()

        if self.verbosity >= 2:
            self.stdout.write(
                'Creating new permissions...'
            )
        Permission.objects.bulk_create(self.defined_permissions)

        if self.verbosity >= 1:
            self.stdout.write(
                'PSEA permissions updated ({}) -> ({}).'.format(
                    old_permissions_count,
                    len(self.defined_permissions),
                )
            )

    def assign_permissions(self):
        # final report. everybody can view. focal point can add action points
        final_assessment_condition = self.assessment_status(
            Assessment.STATUS_FINAL,
        )
        # self.add_permissions(
        #     self.everybody,
        #     'view',
        #     self.report_block,
        #     condition=final_assessment_condition
        # )
        self.add_permissions(
            self.all_unicef_users,
            'view',
            self.follow_up_page,
            # condition=final_assessment_condition
        )
        self.add_permissions(
            self.focal_point,
            'edit',
            self.follow_up_editable_page,
            condition=final_assessment_condition
        )

        # action points related permissions. editable by focal point, author,
        # assignee and assigner
        opened_action_point_condition = self.action_point_status(
            AssessmentActionPoint.STATUSES.open,
        )

        self.add_permissions(
            self.focal_point,
            'edit',
            self.action_points_block,
            condition=self.new_action_point(),
        )
        self.add_permissions(
            self.action_points_editors,
            'edit',
            self.action_points_block,
            condition=opened_action_point_condition
        )
        self.add_permissions(
            [self.focal_point, self.action_point_assignee],
            'action',
            'psea.assessmentactionpoint.complete',
            condition=opened_action_point_condition
        )
