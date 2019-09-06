from django.core.management import BaseCommand
from django.db.models import Q

from etools.applications.action_points.conditions import (
    ActionPointAssignedByCondition,
    ActionPointAssigneeCondition,
    ActionPointAuthorCondition,
)
from etools.applications.action_points.models import ActionPoint
from etools.applications.permissions2.conditions import GroupCondition, NewObjectCondition, ObjectStatusCondition
from etools.applications.permissions2.models import Permission
from etools.applications.permissions2.utils import get_model_target
from etools.applications.tpm.conditions import (
    TPMModuleCondition,
    TPMStaffMemberCondition,
    TPMVisitTPMFocalPointCondition,
    TPMVisitUNICEFFocalPointCondition,
)
from etools.applications.tpm.models import PME, ThirdPartyMonitor, TPMActionPoint, TPMVisit, UNICEFUser


class Command(BaseCommand):
    tpm_partner = [
        'tpmpartners.tpmpartner.*',
        'tpmpartners.tpmpartnerstaffmember.*',
    ]

    visits_list = [
        'tpm.tpmvisit.reference_number',
        'tpm.tpmvisit.tpm_partner',
        'tpm.tpmvisit.implementing_partners',
        'tpm.tpmvisit.status',
        'tpm.tpmvisit.status_date',
        'tpm.tpmvisit.locations',
        'tpm.tpmvisit.sections',
        'tpm.tpmvisit.unicef_focal_points',
        'tpm.tpmvisit.tpm_partner_focal_points',
    ]

    status_dates = [
        'tpm.tpmvisit.date_created',
        'tpm.tpmvisit.date_of_assigned',
        'tpm.tpmvisit.date_of_cancelled',
        'tpm.tpmvisit.date_of_tpm_accepted',
        'tpm.tpmvisit.date_of_tpm_rejected',
        'tpm.tpmvisit.date_of_tpm_reported',
        'tpm.tpmvisit.date_of_tpm_report_rejected',
        'tpm.tpmvisit.date_of_unicef_approved',
    ]

    visit_create = [
        'tpm.tpmvisit.tpm_partner'
    ]

    visit_overview_editable = [
        'tpm.tpmvisit.start_date',
        'tpm.tpmvisit.end_date',

        'tpm.tpmvisit.tpm_partner_focal_points',
        'tpm.tpmvisit.visit_information',
    ]

    visit_overview = visit_overview_editable + [
        'tpm.tpmvisit.reference_number'
        'tpm.tpmvisit.tpm_partner'
    ]

    activities_block = [
        'tpm.tpmvisit.tpm_activities',

        'tpm.tpmactivity.partner',
        'tpm.tpmactivity.intervention',
        'tpm.tpmactivity.cp_output',
        'tpm.tpmactivity.section',
        'tpm.tpmactivity.date',
        'tpm.tpmactivity.locations',
        'tpm.tpmactivity.additional_information',
        'tpm.tpmactivity.offices',
        'tpm.tpmactivity.unicef_focal_points',

        'tpm.tpmactivity._delete',
    ]

    visit_attachments = [
        'tpm.tpmvisit.attachments',
        'tpm.tpmactivity.attachments',
    ]

    visit_report = [
        'tpm.tpmvisit.report_attachments',
        'tpm.tpmvisit.tpm_activities',
        'tpm.tpmactivity.report_attachments',
    ]

    action_points_block = [
        'tpm.tpmvisit.tpm_activities',
        'tpm.tpmactivity.action_points',
        'tpm.tpmactionpoint.*',
    ]

    tpm_visit_details_editable = visit_overview_editable + activities_block + visit_attachments
    tpm_visit_details = visit_overview + activities_block + visit_attachments + status_dates

    focal_point = 'focal_point'
    unicef_user = 'unicef_user'
    pme = 'pme'
    third_party_monitor = 'third_party_monitor'
    third_party_focal_point = 'third_party_focal_point'

    action_point_author = 'action_point_author'
    action_point_assignee = 'action_point_assignee'
    action_point_assigned_by = 'action_point_assigned_by'

    user_roles = {
        pme: [GroupCondition.predicate_template.format(group=PME.name)],

        unicef_user: [GroupCondition.predicate_template.format(group=UNICEFUser.name)],

        focal_point: [GroupCondition.predicate_template.format(group=UNICEFUser.name),
                      TPMVisitUNICEFFocalPointCondition.predicate],

        third_party_monitor: [GroupCondition.predicate_template.format(group=ThirdPartyMonitor.name),
                              TPMStaffMemberCondition.predicate],

        third_party_focal_point: [GroupCondition.predicate_template.format(group=ThirdPartyMonitor.name),
                                  TPMStaffMemberCondition.predicate,
                                  TPMVisitTPMFocalPointCondition.predicate],

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

        condition = (condition or []) + [TPMModuleCondition()] + self.user_roles[role]

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

    def add_permissions(self, role, perm, targets, condition=None):
        self._update_permissions(role, perm, targets, 'allow', condition)

    def revoke_permissions(self, role, perm, targets, condition=None):
        self._update_permissions(role, perm, targets, 'disallow', condition)

    def visit_status(self, status):
        obj = get_model_target(TPMVisit)
        return [ObjectStatusCondition.predicate_template.format(obj=obj, status=status)]

    def new_visit(self):
        model = get_model_target(TPMVisit)
        return [NewObjectCondition.predicate_template.format(model=model)]

    def new_action_point(self):
        model = get_model_target(TPMActionPoint)
        return [NewObjectCondition.predicate_template.format(model=model)]

    def action_point_status(self, status):
        # root status class should be used here for proper condition work
        obj = get_model_target(ActionPoint)
        return [ObjectStatusCondition.predicate_template.format(obj=obj, status=status)]

    def handle(self, *args, **options):
        self.verbosity = options.get('verbosity', 1)

        self.defined_permissions = []

        if self.verbosity >= 2:
            print(
                'Generating new permissions...'
            )

        self.assign_permissions()

        old_permissions = Permission.objects.filter(
            Q(target__startswith='tpm.') |
            Q(target__startswith='tpmpartners.')
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
                'TPM permissions updated ({}) -> ({}).'.format(old_permissions_count, len(self.defined_permissions))
            )

    def assign_permissions(self):
        # common permissions
        # everybody can view partner details, pme can edit
        self.add_permissions([self.unicef_user, self.third_party_monitor], 'view', self.tpm_partner)
        self.add_permissions(self.pme, 'edit', self.tpm_partner)

        # unicef users can view all, tpm can view list fields
        self.add_permissions(self.unicef_user, 'view', self.visits_list + self.tpm_visit_details + self.visit_report)
        self.add_permissions(self.third_party_monitor, 'view', self.visits_list)

        # new visit
        self.add_permissions(self.pme, 'edit', self.visit_create,
                             condition=self.new_visit())

        # draft visit
        self.add_permissions(self.pme, 'edit', self.tpm_visit_details_editable,
                             condition=self.visit_status(TPMVisit.STATUSES.draft))
        self.add_permissions(self.third_party_monitor, 'view', self.tpm_visit_details,
                             condition=self.visit_status(TPMVisit.STATUSES.draft))
        self.add_permissions(self.pme, 'action', ['tpm.tpmvisit.assign', 'tpm.tpmvisit.cancel'],
                             condition=self.visit_status(TPMVisit.STATUSES.draft))
        self.add_permissions(self.pme, 'view', ['tpm.tpmvisit.cancel_comment'],
                             condition=self.visit_status(TPMVisit.STATUSES.draft))

        # visit cancelled
        tpm_cancelled_condition = self.visit_status(TPMVisit.STATUSES.cancelled)
        self.add_permissions([self.unicef_user, self.third_party_monitor], 'view', ['tpm.tpmvisit.cancel_comment'],
                             condition=self.visit_status(TPMVisit.STATUSES.cancelled))
        self.add_permissions(self.third_party_monitor, 'view', self.tpm_visit_details,
                             condition=tpm_cancelled_condition)
        self.add_permissions(self.third_party_monitor, 'view', self.visit_report,
                             condition=tpm_cancelled_condition)

        # visit assigned
        self.add_permissions(self.third_party_monitor, 'view', self.tpm_visit_details,
                             condition=self.visit_status(TPMVisit.STATUSES.assigned))
        self.add_permissions(self.pme, 'edit', self.tpm_visit_details_editable,
                             condition=self.visit_status(TPMVisit.STATUSES.assigned))
        self.add_permissions(self.pme, 'action', 'tpm.tpmvisit.cancel',
                             condition=self.visit_status(TPMVisit.STATUSES.assigned))
        self.add_permissions(self.pme, 'view', ['tpm.tpmvisit.cancel_comment'],
                             condition=self.visit_status(TPMVisit.STATUSES.assigned))
        self.add_permissions(self.third_party_focal_point, 'action', ['tpm.tpmvisit.accept', 'tpm.tpmvisit.reject'],
                             condition=self.visit_status(TPMVisit.STATUSES.assigned))
        self.add_permissions(self.third_party_focal_point, 'view', ['tpm.tpmvisit.reject_comment'],
                             condition=self.visit_status(TPMVisit.STATUSES.assigned))

        # tpm rejected
        self.add_permissions([self.unicef_user, self.third_party_monitor], 'view', ['tpm.tpmvisit.reject_comment'],
                             condition=self.visit_status(TPMVisit.STATUSES.tpm_rejected))
        self.add_permissions(self.pme, 'edit', self.tpm_visit_details_editable,
                             condition=self.visit_status(TPMVisit.STATUSES.tpm_rejected))
        self.add_permissions(self.third_party_monitor, 'view', self.tpm_visit_details,
                             condition=self.visit_status(TPMVisit.STATUSES.tpm_rejected))
        self.add_permissions(self.pme, 'action', ['tpm.tpmvisit.assign', 'tpm.tpmvisit.cancel'],
                             condition=self.visit_status(TPMVisit.STATUSES.tpm_rejected))
        self.add_permissions(self.pme, 'view', ['tpm.tpmvisit.cancel_comment'],
                             condition=self.visit_status(TPMVisit.STATUSES.tpm_rejected))

        # tpm accepted
        self.add_permissions(self.third_party_monitor, 'view', self.tpm_visit_details,
                             condition=self.visit_status(TPMVisit.STATUSES.tpm_accepted))
        self.add_permissions(self.third_party_focal_point, 'edit', self.visit_report,
                             condition=self.visit_status(TPMVisit.STATUSES.tpm_accepted))
        self.add_permissions(self.third_party_focal_point, 'action', 'tpm.tpmvisit.send_report',
                             condition=self.visit_status(TPMVisit.STATUSES.tpm_accepted))

        self.add_permissions(self.pme, 'action', 'tpm.tpmvisit.cancel',
                             condition=self.visit_status(TPMVisit.STATUSES.tpm_accepted))
        self.add_permissions(self.pme, 'view', ['tpm.tpmvisit.cancel_comment'],
                             condition=self.visit_status(TPMVisit.STATUSES.tpm_accepted))

        # tpm reported
        tpm_reported_condition = self.visit_status(TPMVisit.STATUSES.tpm_reported)
        self.add_permissions(self.third_party_monitor, 'view', self.tpm_visit_details,
                             condition=tpm_reported_condition)
        self.add_permissions(self.third_party_monitor, 'view', self.visit_report,
                             condition=tpm_reported_condition)

        self.add_permissions(self.unicef_user, 'view', self.action_points_block,
                             condition=tpm_reported_condition)

        self.add_permissions([self.pme, self.focal_point], 'view', 'tpm.tpmactivity.pv_applicable',
                             condition=tpm_reported_condition)
        self.add_permissions([self.pme, self.focal_point], 'edit',
                             ['tpm.tpmvisit.approval_comment', 'tpm.tpmvisit.report_reject_comments'],
                             condition=tpm_reported_condition)
        self.add_permissions([self.pme, self.focal_point], 'action',
                             ['tpm.tpmvisit.approve', 'tpm.tpmvisit.reject_report'],
                             condition=tpm_reported_condition)

        # report rejected
        self.add_permissions([self.unicef_user, self.third_party_monitor], 'view',
                             ['tpm.tpmvisit.report_reject_comments'],
                             condition=self.visit_status(TPMVisit.STATUSES.tpm_report_rejected))

        self.add_permissions(self.third_party_monitor, 'view', self.tpm_visit_details,
                             condition=self.visit_status(TPMVisit.STATUSES.tpm_report_rejected))
        self.add_permissions(self.third_party_focal_point, 'edit', self.visit_report,
                             condition=self.visit_status(TPMVisit.STATUSES.tpm_report_rejected))
        self.add_permissions(self.third_party_focal_point, 'action', 'tpm.tpmvisit.send_report',
                             condition=self.visit_status(TPMVisit.STATUSES.tpm_report_rejected))

        # unicef approved
        unicef_approved_condition = self.visit_status(TPMVisit.STATUSES.unicef_approved)
        self.add_permissions(self.third_party_monitor, 'view', self.tpm_visit_details,
                             condition=unicef_approved_condition)
        self.add_permissions(self.third_party_monitor, 'view', self.visit_report,
                             condition=unicef_approved_condition)
        self.add_permissions(self.unicef_user, 'view', self.action_points_block + [
            'tpm.tpmvisit.approval_comment'
        ], condition=unicef_approved_condition)

        # action points specific permissions. pme and action points can do everything.
        # author, assignee and assigner can edit. assignee can complete.
        for editable_condition in [tpm_reported_condition, unicef_approved_condition]:
            self.add_permissions(
                [self.pme, self.focal_point],
                'edit', [
                    'tpm.tpmvisit.tpm_activities',
                    'tpm.tpmactivity.action_points',
                ],
                condition=editable_condition
            )

            self.add_permissions(
                [self.pme, self.focal_point],
                'edit', 'tpm.tpmactionpoint.*',
                condition=editable_condition + self.new_action_point()
            )

        self.add_permissions(
            [self.pme, self.focal_point, self.action_point_author,
             self.action_point_assignee, self.action_point_assigned_by],
            'edit', self.action_points_block,
            condition=self.action_point_status(TPMActionPoint.STATUSES.open)
        )

        self.add_permissions(
            [self.pme, self.focal_point, self.action_point_assignee],
            'action', 'tpm.tpmactionpoint.complete',
            condition=self.action_point_status(TPMActionPoint.STATUSES.open)
        )
