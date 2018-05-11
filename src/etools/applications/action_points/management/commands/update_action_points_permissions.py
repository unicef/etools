from django.core.management import BaseCommand

from etools.applications.action_points.conditions import (
    ActionPointAssignedByCondition, ActionPointAssigneeCondition, ActionPointAuthorCondition,)
from etools.applications.action_points.models import ActionPoint, PME, UNICEFUser
from etools.applications.permissions2.conditions import GroupCondition, NewObjectCondition, ObjectStatusCondition
from etools.applications.permissions2.models import Permission


class Command(BaseCommand):
    action_point_pmp_relations = [
        'action_points.actionpoint.cp_output',
        'action_points.actionpoint.partner',
        'action_points.actionpoint.intervention',
        'action_points.actionpoint.location',
        'action_points.actionpoint.section',
        'action_points.actionpoint.office',
    ]

    # editable fields on create
    action_point_create = [
        'action_points.actionpoint.description',
        'action_points.actionpoint.due_date',
        'action_points.actionpoint.assigned_to',
        'action_points.actionpoint.high_priority',
    ] + action_point_pmp_relations

    # editable fields on edit
    action_point_edit = [
        'action_points.actionpoint.due_date',
        'action_points.actionpoint.assigned_to',
        'action_points.actionpoint.action_taken',
        'action_points.actionpoint.high_priority',
    ] + action_point_pmp_relations

    # common fields, should be visible always
    action_point_list = [
        'action_points.actionpoint.reference_number',
        'action_points.actionpoint.related_module',
        'action_points.actionpoint.description',
        'action_points.actionpoint.due_date',
        'action_points.actionpoint.assigned_to',
        'action_points.actionpoint.author',
        'action_points.actionpoint.assigned_by',
        'action_points.actionpoint.high_priority',

        'action_points.actionpoint.status',
        'action_points.actionpoint.status_date',
    ] + action_point_pmp_relations

    # object details specific fields
    action_point_details = [
        'action_points.actionpoint.related_object_str',
        'action_points.actionpoint.related_object_url',

        'action_points.actionpoint.action_taken',
        'action_points.actionpoint.created',
        'action_points.actionpoint.date_of_completion',

        'action_points.actionpoint.comments',
        'action_points.actionpoint.history',
    ]

    unicef_user = 'unicef_user'
    pme = 'pme'
    author = 'author'
    assigned_by = 'assigned_by'
    assignee = 'assignee'

    user_roles = {
        pme: [GroupCondition.predicate_template.format(group=PME.name)],
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

        if condition is None:
            condition = []
        else:
            condition = condition[:]

        condition.extend(self.user_roles[role])

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

        self.permissions.extend([
            Permission(target=target, permission=perm, permission_type=perm_type, condition=condition)
            for target in targets
        ])

    def add_permission(self, role, perm, targets, condition=None):
        self._update_permissions(role, perm, targets, 'allow', condition)

    def revoke_permission(self, role, perm, targets, condition=None):
        self._update_permissions(role, perm, targets, 'disallow', condition)

    def action_point_status(self, status):
        obj = '{}_{}'.format(ActionPoint._meta.app_label, ActionPoint._meta.model_name)
        return [ObjectStatusCondition.predicate_template.format(obj=obj, status=status)]

    def new_action_point(self):
        model = '{}_{}'.format(ActionPoint._meta.app_label, ActionPoint._meta.model_name)
        return [NewObjectCondition.predicate_template.format(model=model)]

    def handle(self, *args, **options):
        self.verbosity = options.get('verbosity', 1)

        self.permissions = []

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
        Permission.objects.bulk_create(self.permissions)

        if self.verbosity >= 1:
            self.stdout.write(
                'Action Points permissions updated ({}) -> ({}).'.format(old_permissions_count, len(self.permissions))
            )

    def assign_permissions(self):
        self.add_permission([self.unicef_user, self.pme], 'view',
                            self.action_point_list + self.action_point_details)

        self.add_permission(self.unicef_user, 'edit', self.action_point_create,
                            condition=self.new_action_point())

        self.add_permission([self.pme, self.author, self.assigned_by, self.assignee], 'edit', self.action_point_edit,
                            condition=self.action_point_status(ActionPoint.STATUSES.open))
        self.add_permission([self.pme, self.assignee], 'action', 'action_points.actionpoint.complete')
