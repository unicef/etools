
from django.core.management import BaseCommand
from django.db.models import Q
from django.utils import six

from etools.applications.permissions2.models import Permission
from etools.applications.permissions2.conditions import ObjectStatusCondition, \
    NewObjectCondition, GroupCondition
from etools.applications.tpm.conditions import TPMStaffMemberCondition, TPMVisitUNICEFFocalPointCondition, TPMVisitTPMFocalPointCondition
from etools.applications.tpm.models import UNICEFUser, PME, ThirdPartyMonitor, TPMVisit


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

    tpm_visit_details_editable = visit_overview_editable + activities_block + visit_attachments
    tpm_visit_details = visit_overview + activities_block + visit_attachments + status_dates

    focal_point = 'focal_point'
    unicef_user = 'unicef_user'
    pme = 'pme'
    third_party_monitor = 'third_party_monitor'
    third_party_focal_point = 'third_party_focal_point'

    user_roles = {
        pme: [GroupCondition.predicate_template.format(group=PME.name)],

        unicef_user: [GroupCondition.predicate_template.format(group=UNICEFUser.name)],

        focal_point: [GroupCondition.predicate_template.format(group=UNICEFUser.name),
                      TPMVisitUNICEFFocalPointCondition.predicate],

        third_party_monitor: [GroupCondition.predicate_template.format(group=ThirdPartyMonitor.name),
                              TPMStaffMemberCondition.predicate],

        third_party_focal_point: [GroupCondition.predicate_template.format(group=ThirdPartyMonitor.name),
                                  TPMStaffMemberCondition.predicate,
                                  TPMVisitTPMFocalPointCondition.predicate]
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
        Permission.objects.bulk_create(self.permissions)

        if self.verbosity >= 1:
            self.stdout.write(
                'TPM permissions updated ({}) -> ({}).'.format(old_permissions_count, len(self.permissions))
            )

    def assign_permissions(self):
        # common permissions
        # everybody can view partner details, pme can edit
        self.add_permission([self.unicef_user, self.third_party_monitor], 'view', self.tpm_partner)
        self.add_permission(self.pme, 'edit', self.tpm_partner)

        # unicef users can view all, tpm can view list fields
        self.add_permission(self.unicef_user, 'view', self.visits_list + self.tpm_visit_details)
        self.add_permission(self.third_party_monitor, 'view', self.visits_list)

        # new visit
        self.add_permission(self.pme, 'edit', self.visit_create,
                            condition=self.new_visit())

        # draft visit
        self.add_permission(self.pme, 'edit', self.tpm_visit_details_editable,
                            condition=self.visit_status(TPMVisit.STATUSES.draft))
        self.add_permission(self.third_party_monitor, 'view', self.tpm_visit_details,
                            condition=self.visit_status(TPMVisit.STATUSES.draft))
        self.add_permission(self.pme, 'action', ['tpm.tpmvisit.assign', 'tpm.tpmvisit.cancel'],
                            condition=self.visit_status(TPMVisit.STATUSES.draft))

        # visit cancelled
        self.add_permission([self.unicef_user, self.third_party_monitor], 'view', ['tpm.tpmvisit.cancel_comment'],
                            condition=self.visit_status(TPMVisit.STATUSES.cancelled))

        # visit assigned
        self.add_permission(self.third_party_monitor, 'view', self.tpm_visit_details,
                            condition=self.visit_status(TPMVisit.STATUSES.assigned))
        self.add_permission(self.pme, 'action', 'tpm.tpmvisit.cancel',
                            condition=self.visit_status(TPMVisit.STATUSES.assigned))
        self.add_permission(self.third_party_focal_point, 'action', ['tpm.tpmvisit.accept', 'tpm.tpmvisit.reject'],
                            condition=self.visit_status(TPMVisit.STATUSES.assigned))

        # tpm rejected
        self.add_permission([self.unicef_user, self.third_party_monitor], 'view', ['tpm.tpmvisit.reject_comment'],
                            condition=self.visit_status(TPMVisit.STATUSES.tpm_rejected))
        self.add_permission(self.pme, 'edit', self.tpm_visit_details_editable,
                            condition=self.visit_status(TPMVisit.STATUSES.tpm_rejected))
        self.add_permission(self.third_party_monitor, 'view', self.tpm_visit_details,
                            condition=self.visit_status(TPMVisit.STATUSES.tpm_rejected))
        self.add_permission(self.pme, 'action', ['tpm.tpmvisit.assign', 'tpm.tpmvisit.cancel'],
                            condition=self.visit_status(TPMVisit.STATUSES.tpm_rejected))

        # tpm accepted
        self.add_permission(self.third_party_monitor, 'view', self.tpm_visit_details,
                            condition=self.visit_status(TPMVisit.STATUSES.tpm_accepted))
        self.add_permission(self.third_party_focal_point, 'edit', self.visit_report,
                            condition=self.visit_status(TPMVisit.STATUSES.tpm_accepted))
        self.add_permission(self.third_party_focal_point, 'action', 'tpm.tpmvisit.send_report',
                            condition=self.visit_status(TPMVisit.STATUSES.tpm_accepted))

        self.add_permission(self.pme, 'action', 'tpm.tpmvisit.cancel',
                            condition=self.visit_status(TPMVisit.STATUSES.tpm_accepted))

        # tpm reported
        self.add_permission(self.third_party_monitor, 'view', self.tpm_visit_details,
                            condition=self.visit_status(TPMVisit.STATUSES.tpm_reported))
        self.add_permission([self.unicef_user, self.third_party_monitor], 'view', self.visit_report,
                            condition=self.visit_status(TPMVisit.STATUSES.tpm_reported))

        self.add_permission([self.pme, self.focal_point], 'edit', 'tpm.tpmvisit.action_points',
                            condition=self.visit_status(TPMVisit.STATUSES.tpm_reported))
        self.add_permission(self.unicef_user, 'view', 'tpm.tpmvisit.action_points',
                            condition=self.visit_status(TPMVisit.STATUSES.tpm_reported))

        self.add_permission(self.pme, 'view', 'tpm.tpmactivity.pv_applicable',
                            condition=self.visit_status(TPMVisit.STATUSES.tpm_reported))
        self.add_permission(self.pme, 'edit', 'tpm.tpmvisit.approval_comment',
                            condition=self.visit_status(TPMVisit.STATUSES.tpm_reported))
        self.add_permission(self.pme, 'action',
                            ['tpm.tpmvisit.approve', 'tpm.tpmvisit.reject_report'],
                            condition=self.visit_status(TPMVisit.STATUSES.tpm_reported))

        # report rejected
        self.add_permission([self.unicef_user, self.third_party_monitor], 'view',
                            ['tpm.tpmvisit.report_reject_comments'],
                            condition=self.visit_status(TPMVisit.STATUSES.tpm_report_rejected))
        self.add_permission(self.unicef_user, 'view', self.visit_report,
                            condition=self.visit_status(TPMVisit.STATUSES.tpm_report_rejected))

        self.add_permission(self.third_party_monitor, 'view', self.tpm_visit_details,
                            condition=self.visit_status(TPMVisit.STATUSES.tpm_report_rejected))
        self.add_permission(self.third_party_focal_point, 'edit', self.visit_report,
                            condition=self.visit_status(TPMVisit.STATUSES.tpm_report_rejected))
        self.add_permission(self.third_party_focal_point, 'action', 'tpm.tpmvisit.send_report',
                            condition=self.visit_status(TPMVisit.STATUSES.tpm_report_rejected))

        # unicef approved
        self.add_permission(self.third_party_monitor, 'view', self.tpm_visit_details,
                            condition=self.visit_status(TPMVisit.STATUSES.unicef_approved))
        self.add_permission([self.unicef_user, self.third_party_monitor], 'view', self.visit_report,
                            condition=self.visit_status(TPMVisit.STATUSES.unicef_approved))
        self.add_permission(self.unicef_user, 'view', ['tpm.tpmvisit.action_points', 'tpm.tpmvisit.approval_comment'],
                            condition=self.visit_status(TPMVisit.STATUSES.unicef_approved))
