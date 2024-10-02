from django.core.management import BaseCommand

from etools.applications.action_points.conditions import (
    ActionPointAssignedByCondition,
    ActionPointAssigneeCondition,
    ActionPointAuthorCondition,
    ActionPointModuleCondition,
    ActionPointNotAuthorCondition,
    ActionPointPotentialVerifierCondition,
    AuthorIsAssignee,
    CompleteHighPriorityActionPointAttachmentCondition,
    HighPriorityActionPointCondition,
    LowPriorityActionPointCondition,
    NotVerifiedActionPointCondition,
    PotentialVerifierProvidedCondition,
    RelatedActionPointCondition,
    UnRelatedActionPointCondition,
    VerifiedActionPointCondition,
)
from etools.applications.action_points.models import ActionPoint, OperationsGroup, PME, UNICEFUser
from etools.applications.permissions2.conditions import GroupCondition, NewObjectCondition, ObjectStatusCondition
from etools.applications.permissions2.models import Permission
from etools.applications.permissions2.utils import get_model_target


class Command(BaseCommand):
    action_point_pmp_relations = [
        'action_points.actionpoint.cp_output',
        'action_points.actionpoint.partner',
        'action_points.actionpoint.intervention',
        'action_points.actionpoint.location',
    ]

    action_point_related_objects = [
        'action_points.actionpoint.engagement',
        'action_points.actionpoint.tpm_activity',
        'action_points.actionpoint.psea_assessment',
        'action_points.actionpoint.travel_activity',
    ]

    # editable fields on create
    action_point_create = [
        'action_points.actionpoint.category',
        'action_points.actionpoint.description',
        'action_points.actionpoint.due_date',
        'action_points.actionpoint.assigned_to',
        'action_points.actionpoint.high_priority',
        'action_points.actionpoint.section',
        'action_points.actionpoint.office',
    ] + action_point_pmp_relations + action_point_related_objects

    # editable fields on edit
    action_point_base_edit = [
        'action_points.actionpoint.category',
        'action_points.actionpoint.description',
        'action_points.actionpoint.due_date',
        'action_points.actionpoint.assigned_to',
        'action_points.actionpoint.high_priority',
        'action_points.actionpoint.comments',
        'action_points.actionpoint.section',
        'action_points.actionpoint.office',
    ]

    related_action_point_edit = action_point_base_edit
    not_related_action_point_edit = action_point_base_edit + action_point_pmp_relations

    # common fields, should be visible always
    action_point_list = [
        'action_points.actionpoint.reference_number',
        'action_points.actionpoint.related_module',
        'action_points.actionpoint.category',
        'action_points.actionpoint.description',
        'action_points.actionpoint.due_date',
        'action_points.actionpoint.assigned_to',
        'action_points.actionpoint.author',
        'action_points.actionpoint.assigned_by',
        'action_points.actionpoint.high_priority',
        'action_points.actionpoint.section',
        'action_points.actionpoint.office',

        'action_points.actionpoint.status',
        'action_points.actionpoint.status_date',
    ] + action_point_pmp_relations + action_point_related_objects

    # object details specific fields
    action_point_details = [
        'action_points.actionpoint.related_object_str',
        'action_points.actionpoint.related_object_url',

        'action_points.actionpoint.created',
        'action_points.actionpoint.date_of_completion',
        'action_points.actionpoint.date_of_verification',
        'action_points.actionpoint.verified_by',
        'action_points.actionpoint.is_adequate',
        'action_points.actionpoint.potential_verifier',

        'action_points.actionpoint.comments',
        'action_points.actionpoint.history',
    ]

    unicef_user = 'unicef_user'
    pme = 'pme'
    operations = 'operations'
    author = 'author'
    assigned_by = 'assigned_by'
    assignee = 'assignee'
    potential_verifier = 'potential_verifier'

    user_roles = {
        pme: [GroupCondition.predicate_template.format(group=PME.name)],
        operations: [GroupCondition.predicate_template.format(group=OperationsGroup.name)],
        potential_verifier: [ActionPointPotentialVerifierCondition.predicate],
        unicef_user: [GroupCondition.predicate_template.format(group=UNICEFUser.name)],
        author: [ActionPointAuthorCondition.predicate],
        assigned_by: [ActionPointAssignedByCondition.predicate],
        assignee: [ActionPointAssigneeCondition.predicate],
    }

    def _update_permissions(self, role, perm, targets, perm_type, condition=None):
        if isinstance(role, (list, tuple)):
            for r in role:
                self._update_permissions(r, perm, targets, perm_type, condition)
            return

        if isinstance(targets, str):
            targets = [targets]

        condition = (condition or []) + [ActionPointModuleCondition()] + self.user_roles[role]

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
            Permission(target=target, permission=perm, permission_type=perm_type, condition=condition)
            for target in targets
        ])

    def add_permission(self, role, perm, targets, condition=None):
        self._update_permissions(role, perm, targets, 'allow', condition)

    def revoke_permission(self, role, perm, targets, condition=None):
        self._update_permissions(role, perm, targets, 'disallow', condition)

    def action_point_status(self, status):
        obj = get_model_target(ActionPoint)
        return [ObjectStatusCondition.predicate_template.format(obj=obj, status=status)]

    def new_action_point(self):
        model = get_model_target(ActionPoint)
        return [NewObjectCondition.predicate_template.format(model=model)]

    def related_action_point(self):
        return [RelatedActionPointCondition.predicate]

    def not_related_action_point(self):
        return [UnRelatedActionPointCondition.predicate]

    def not_verified_action_point(self):
        return [NotVerifiedActionPointCondition.predicate]

    def verified_action_point(self):
        return [VerifiedActionPointCondition.predicate]

    def potential_verifier_provided(self):
        return [PotentialVerifierProvidedCondition.predicate]

    def high_priority_action_point(self):
        return [HighPriorityActionPointCondition.predicate]

    def complete_high_priority_action_point(self):
        return [CompleteHighPriorityActionPointAttachmentCondition.predicate]

    def low_priority_action_point(self):
        return [LowPriorityActionPointCondition.predicate]

    def not_author(self):
        return [ActionPointNotAuthorCondition.predicate]

    def author_is_assignee(self):
        return [AuthorIsAssignee.predicate]

    def handle(self, *args, **options):
        self.verbosity = options.get('verbosity', 1)

        self.defined_permissions = []

        if self.verbosity >= 2:
            print(
                'Generating new permissions...'
            )

        self.assign_permissions()

        old_permissions = Permission.objects.filter(target__startswith='action_points.')
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
                'Action Points permissions updated ({}) -> ({}).'.format(
                    old_permissions_count, len(self.defined_permissions)
                )
            )

    def assign_permissions(self):
        self.add_permission([self.unicef_user, self.pme], 'view',
                            self.action_point_list + self.action_point_details)

        self.add_permission(self.unicef_user, 'edit', self.action_point_create,
                            condition=self.new_action_point())

        self.add_permission(
            [self.pme, self.author, self.assigned_by, self.assignee],
            'edit',
            self.related_action_point_edit,
            condition=self.action_point_status(ActionPoint.STATUSES.open) + self.related_action_point()
        )
        self.add_permission(
            [self.pme, self.author, self.assigned_by, self.assignee],
            'edit',
            self.not_related_action_point_edit,
            condition=self.action_point_status(ActionPoint.STATUSES.open) + self.not_related_action_point()
        )

        # completion is different for high & low priority action points
        self.add_permission(
            [self.pme, self.assigned_by, self.assignee, self.author],
            'action',
            'action_points.actionpoint.complete',
            condition=self.action_point_status(ActionPoint.STATUSES.open) + self.low_priority_action_point()
        )

        # high priority action points permissions

        # author with PME group shouldn't be able to verify
        self.add_permission(
            [self.pme, self.operations, self.potential_verifier],
            'edit',
            'action_points.actionpoint.is_adequate',
            condition=self.action_point_status(ActionPoint.STATUSES.open) + self.high_priority_action_point() + self.not_author() + self.not_verified_action_point()
        )

        # if author is assignee, allow edit for potential verifier
        self.add_permission(
            [self.pme, self.assigned_by, self.assignee, self.author],
            'edit',
            'action_points.actionpoint.potential_verifier',
            condition=self.action_point_status(ActionPoint.STATUSES.open) + self.high_priority_action_point() + self.author_is_assignee()
        )

        # complete transition allowed for same author and assignee, only if it has been verified
        self.add_permission(
            [self.pme, self.assigned_by, self.assignee, self.author, self.potential_verifier],
            'action',
            'action_points.actionpoint.complete',
            condition=self.action_point_status(ActionPoint.STATUSES.open) + self.complete_high_priority_action_point() + self.verified_action_point()
        )
