from django.core.management import BaseCommand
from django.utils import six

from permissions2.models import Permission
from permissions2.conditions import TPMRoleCondition, TPMStaffMemberCondition, ObjectStatusCondition, \
    NewObjectCondition, TPMVisitUNICEFFocalPointCondition

from tpm.models import UNICEFUser, PME, ThirdPartyMonitor, TPMVisit


class Command(BaseCommand):
    tpm_partner = [
        'tpmpartner.*',
        'tpmpartnerstaffmember.*',
    ]

    tpm_visit = [
        'tpmvisit.*',
        'tpmactivity.*',
    ]

    tpm_visit_details = [
        'tpmvisit.tpm_partner',
        'tpmvisit.tpm_activities',
        'tpmvisit.status',
        'tpmvisit.attachments',
        'tpmvisit.unicef_focal_points',
        'tpmvisit.tpm_partner_focal_points',
        'tpmvisit.offices',
        'tpmactivity.*',
    ]

    tpm_action_points = [
        'tpmvisit.tpm_activities',
        'tpmactivity.action_points',
        'tpmactivityactionpoint.*',
    ]

    focal_point = 'focal_point'
    unicef_user = 'unicef_user'
    pme = 'pme'
    third_party_monitor = 'third_party_monitor'
    user_roles = {
        pme: [TPMRoleCondition.predicate_template.format(role=PME.name)],
        unicef_user: [TPMRoleCondition.predicate_template.format(role=UNICEFUser.name)],
        focal_point: [TPMRoleCondition.predicate_template.format(role=UNICEFUser.name),
                      TPMVisitUNICEFFocalPointCondition.predicate],
        third_party_monitor: [TPMRoleCondition.predicate_template.format(role=ThirdPartyMonitor.name),
                              TPMStaffMemberCondition.predicate],
    }

    def __init__(self, *args, **kwargs):
        super(Command, self).__init__(*args, **kwargs)

        self.permissions = []

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
        verbosity = options.get('verbosity', 1)

        self.add_permission([self.unicef_user, self.third_party_monitor], 'view', self.tpm_partner)
        self.add_permission(self.pme, 'edit', self.tpm_partner)

        self.add_permission(self.pme, 'action', ['tpmpartner.activate', 'tpmpartner.cancel'])

        self.add_permission(self.pme, 'edit', self.tpm_visit_details,
                            condition=self.new_visit())

        self.add_permission(self.pme, 'edit', self.tpm_visit_details,
                            condition=self.visit_status(TPMVisit.STATUSES.draft))
        self.add_permission(self.unicef_user, 'view', self.tpm_visit_details,
                            condition=self.visit_status(TPMVisit.STATUSES.draft))
        self.add_permission(self.pme, 'action', 'tpmvisit.assign',
                            condition=self.visit_status(TPMVisit.STATUSES.draft))

        self.add_permission([self.pme, self.unicef_user, self.third_party_monitor], 'view', self.tpm_visit_details,
                            condition=self.visit_status(TPMVisit.STATUSES.assigned))
        self.add_permission(self.third_party_monitor, 'action', ['tpmvisit.accept', 'tpmvisit.reject'],
                            condition=self.visit_status(TPMVisit.STATUSES.assigned))

        self.add_permission([self.pme, self.unicef_user, self.third_party_monitor], 'view', self.tpm_visit_details,
                            condition=self.visit_status(TPMVisit.STATUSES.tpm_accepted))
        self.add_permission(self.third_party_monitor, 'action', 'tpmvisit.send_report',
                            condition=self.visit_status(TPMVisit.STATUSES.tpm_accepted))

        self.add_permission(self.pme, 'edit', self.tpm_visit_details,
                            condition=self.visit_status(TPMVisit.STATUSES.tpm_rejected))
        self.add_permission([self.unicef_user, self.third_party_monitor], 'view', self.tpm_visit_details,
                            condition=self.visit_status(TPMVisit.STATUSES.tpm_rejected))
        self.add_permission(self.pme, 'action', 'tpmvisit.assign',
                            condition=self.visit_status(TPMVisit.STATUSES.tpm_rejected))

        self.add_permission([self.pme, self.unicef_user, self.third_party_monitor], 'view', self.tpm_visit_details,
                            condition=self.visit_status(TPMVisit.STATUSES.tpm_reported))
        self.add_permission(self.pme, 'action', ['tpmvisit.approve', 'tpmvisit.reject_report'],
                            condition=self.visit_status(TPMVisit.STATUSES.tpm_reported))

        self.add_permission([self.pme, self.unicef_user, self.third_party_monitor], 'view', self.tpm_visit_details,
                            condition=self.visit_status(TPMVisit.STATUSES.tpm_report_rejected))
        self.add_permission(self.third_party_monitor, 'action', 'tpmvisit.send_report',
                            condition=self.visit_status(TPMVisit.STATUSES.tpm_report_rejected))

        self.add_permission([self.pme, self.unicef_user], 'view', self.tpm_visit_details,
                            condition=self.visit_status(TPMVisit.STATUSES.unicef_approved))

        self.add_permission(self.pme, 'action', 'tpmvisit.cancel')

        self.add_permission([self.pme, self.focal_point], 'edit', self.tpm_action_points,
                            condition=self.visit_status(TPMVisit.STATUSES.tpm_reported))

        Permission.objects.bulk_create(self.permissions)
