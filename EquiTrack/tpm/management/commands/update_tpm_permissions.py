from django.core.management import BaseCommand
from django.utils import six

from permissions2.models import Permission
from permissions2.conditions import ObjectStatusCondition, \
    NewObjectCondition, GroupCondition

from ...conditions import TPMStaffMemberCondition, TPMVisitUNICEFFocalPointCondition
from ...models import UNICEFUser, PME, ThirdPartyMonitor, TPMVisit


class Command(BaseCommand):
    tpm_partner = [
        'tpm.tpmpartner.*',
        'tpm.tpmpartnerstaffmember.*',
    ]

    tpm_visit_details = [
        'tpm.tpmvisit.reference_number',
        'tpm.tpmvisit.tpm_partner',
        'tpm.tpmvisit.start_date',
        'tpm.tpmvisit.end_date',
        'tpm.tpmvisit.tpm_activities',
        'tpm.tpmvisit.status',
        'tpm.tpmvisit.unicef_focal_points',
        'tpm.tpmvisit.tpm_partner_focal_points',
        'tpm.tpmvisit.offices',

        'tpm.tpmvisit.date_created',
        'tpm.tpmvisit.date_of_assigned',
        'tpm.tpmvisit.date_of_cancelled',
        'tpm.tpmvisit.date_of_tpm_accepted',
        'tpm.tpmvisit.date_of_tpm_rejected',
        'tpm.tpmvisit.date_of_tpm_reported',
        'tpm.tpmvisit.date_of_tpm_report_rejected',
        'tpm.tpmvisit.date_of_unicef_approved',


        'tpm.tpmactivity.implementing_partner',
        'tpm.tpmactivity.partnership',
        'tpm.tpmactivity.cp_output',
        'tpm.tpmactivity.locations',
        'tpm.tpmactivity.section',
        'tpm.tpmactivity.additional_information',
        'tpm.tpmactivity.date',

        'tpm.tpmvisit.attachments',
        'tpm.tpmactivity.attachments',
    ]

    tpm_visit_report = [
        'tpm.tpmvisit.report_attachments',

        'tpm.tpmvisit.tpm_activities',
        'tpm.tpmactivity.report_attachments',
    ]

    focal_point = 'focal_point'
    unicef_user = 'unicef_user'
    pme = 'pme'
    third_party_monitor = 'third_party_monitor'
    user_roles = {
        pme: [GroupCondition.predicate_template.format(group=PME.name)],
        unicef_user: [GroupCondition.predicate_template.format(group=UNICEFUser.name)],
        focal_point: [GroupCondition.predicate_template.format(group=UNICEFUser.name),
                      TPMVisitUNICEFFocalPointCondition.predicate],
        third_party_monitor: [GroupCondition.predicate_template.format(group=ThirdPartyMonitor.name),
                              TPMStaffMemberCondition.predicate],
    }

    def _update_permissions(self, role, perm, targets, perm_type, condition=None):
        if isinstance(role, (list, tuple)):
            for r in role:
                self._update_permissions(r, perm, targets, perm_type, condition)
            return

        if isinstance(targets, six.string_types):
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

    def visit_status(self, status):
        obj = '{}_{}'.format(TPMVisit._meta.app_label, TPMVisit._meta.model_name)
        return [ObjectStatusCondition.predicate_template.format(obj=obj, status=status)]

    def new_visit(self):
        model = '{}_{}'.format(TPMVisit._meta.app_label, TPMVisit._meta.model_name)
        return [NewObjectCondition.predicate_template.format(model=model)]

    def handle(self, *args, **options):
        self.verbosity = options.get('verbosity', 1)

        self.permissions = []

        if self.verbosity >= 2:
            print(
                'Generating new permissions...'
            )

        self.add_permission([self.unicef_user, self.third_party_monitor], 'view', self.tpm_partner)
        self.add_permission(self.pme, 'edit', self.tpm_partner)

        self.add_permission(self.pme, 'action', ['tpm.tpmpartner.activate', 'tpm.tpmpartner.cancel'])

        self.add_permission([self.unicef_user, self.third_party_monitor], 'view', self.tpm_visit_details)

        self.add_permission(self.pme, 'edit', self.tpm_visit_details,
                            condition=self.new_visit())

        self.add_permission(self.pme, 'edit', self.tpm_visit_details,
                            condition=self.visit_status(TPMVisit.STATUSES.draft))
        self.revoke_permission(self.third_party_monitor, 'view', self.tpm_visit_details,
                               condition=self.visit_status(TPMVisit.STATUSES.draft))

        self.add_permission([self.unicef_user, self.third_party_monitor], 'view', ['tpm.tpmvisit.reject_comment'],
                            condition=self.visit_status(TPMVisit.STATUSES.tpm_rejected))
        self.add_permission(self.pme, 'edit', self.tpm_visit_details,
                            condition=self.visit_status(TPMVisit.STATUSES.tpm_rejected))

        self.add_permission(self.third_party_monitor, 'edit', self.tpm_visit_report,
                            condition=self.visit_status(TPMVisit.STATUSES.tpm_accepted))

        self.add_permission([self.unicef_user, self.third_party_monitor], 'view', self.tpm_visit_report,
                            condition=self.visit_status(TPMVisit.STATUSES.tpm_reported))

        self.add_permission([self.unicef_user, self.third_party_monitor], 'view',
                            ['tpm.tpmvisit.report_reject_comments', 'tpm.tpmvisitreportrejectcomment.*'],
                            condition=self.visit_status(TPMVisit.STATUSES.tpm_report_rejected))
        self.add_permission(self.unicef_user, 'view', self.tpm_visit_report,
                            condition=self.visit_status(TPMVisit.STATUSES.tpm_report_rejected))
        self.add_permission(self.third_party_monitor, 'edit', self.tpm_visit_report,
                            condition=self.visit_status(TPMVisit.STATUSES.tpm_report_rejected))

        self.add_permission([self.unicef_user, self.third_party_monitor], 'view', self.tpm_visit_report,
                            condition=self.visit_status(TPMVisit.STATUSES.unicef_approved))

        self.add_permission([self.pme, self.focal_point], 'edit', 'tpm.tpmvisit.action_points',
                            condition=self.visit_status(TPMVisit.STATUSES.tpm_reported))
        self.add_permission(self.unicef_user, 'view', 'tpm.tpmvisit.action_points',
                            condition=self.visit_status(TPMVisit.STATUSES.tpm_reported))
        self.add_permission(self.unicef_user, 'view', 'tpm.tpmvisit.action_points',
                            condition=self.visit_status(TPMVisit.STATUSES.unicef_approved))

        self.add_permission(self.pme, 'action', 'tpm.tpmvisit.cancel')
        self.add_permission(self.pme, 'action', 'tpm.tpmvisit.assign')
        self.add_permission(self.third_party_monitor, 'action', ['tpm.tpmvisit.accept', 'tpm.tpmvisit.reject'])
        self.add_permission(self.third_party_monitor, 'action', 'tpm.tpmvisit.send_report')
        self.add_permission(self.pme, 'action', ['tpm.tpmvisit.approve', 'tpm.tpmvisit.reject_report'])
        self.add_permission(self.third_party_monitor, 'action', 'tpm.tpmvisit.send_report')

        self.add_permission([self.pme, self.focal_point], 'edit', 'tpm.tpmactionpoint.*')

        old_permissions = Permission.objects.filter(target__startswith='tpm.')
        old_permissions_count = old_permissions.count()

        if self.verbosity >= 2:
            print(
                'Deleting old permissions...'
            )
        old_permissions.delete()

        if self.verbosity >= 2:
            print(
                'Creating new permissions...'
            )
        Permission.objects.bulk_create(self.permissions)

        if self.verbosity >= 1:
            print(
                'TPM permissions updated ({}) -> ({}).'.format(old_permissions_count, len(self.permissions))
            )
