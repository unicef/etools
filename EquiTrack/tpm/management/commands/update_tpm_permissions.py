from django.core.management import BaseCommand
from django.db import connection
from django.utils import six

from tenant_schemas.utils import get_tenant_model

from tpm.models import TPMPermission, UNICEFUser, PME, ThirdPartyMonitor


class Command(BaseCommand):
    help = 'Clean tpm permissions'

    focal_point = 'focal_point'
    unicef_user = 'unicef_user'
    pme = 'pme'
    third_party_monitor = 'third_party_monitor'
    user_roles = {
        focal_point: TPMPermission.USER_TYPES.unicef_focal_point,
        unicef_user: UNICEFUser.code,
        pme: PME.code,
        third_party_monitor: ThirdPartyMonitor.code,
    }

    all_unicef_users = [pme, focal_point, unicef_user]
    everybody = all_unicef_users + [third_party_monitor, ]

    everything = [
        'tpmpartner.*',
        'tpmpartnerstaffmember.*',
        'tpmvisit.*',
        'tpmactivity.*',
        'tpmvisitreportrejectcomment.*',
        'tpmactivityactionpoint.*',
        'tpmactionpoint.*',
    ]

    visit_create = [
        'tpmvisit.tpm_partner',
        'tpmvisit.tpm_activities',
        'tpmvisit.attachments',
        'tpmvisit.unicef_focal_points',
        'tpmvisit.tpm_partner_focal_points',
        'tpmvisit.offices',
        'tpmvisit.sections',
        'tpmvisit.visit_information',
        'tpmactivity.*',
    ]

    follow_up_page = [
        'tpmvisit.action_points',
        'tpmactionpoint.*',
    ]

    new_visit = 'new'
    draft = 'draft'
    assigned = 'assigned'
    cancelled = 'cancelled'
    tpm_accepted = 'tpm_accepted'
    tpm_rejected = 'tpm_rejected'
    tpm_reported = 'tpm_reported'
    tpm_report_rejected = 'tpm_report_rejected'
    unicef_approved = 'unicef_approved'

    def __init__(self, *args, **kwargs):
        super(Command, self).__init__(*args, **kwargs)
        self.permissions = []

    def _get_perm_obj(self, status, role, perm_type, perm, target):
        return TPMPermission(**{
            'instance_status': status,
            'target': target,
            'user_type': self.user_roles[role],
            'permission': perm,
            'permission_type': perm_type
        })

    def _update_permissions(self, status, roles, perm_type, perm, targets):
        if isinstance(roles, six.string_types):
            roles = [roles, ]

        if isinstance(targets, six.string_types):
            targets = [targets, ]

        for role in roles:
            for target in targets:
                existing = filter(
                    lambda p:
                        p.instance_status == status and
                        p.target == target and
                        p.user_type == self.user_roles[role] and
                        p.permission_type == perm_type,
                    self.permissions
                )
                if not existing:
                    self.permissions.append(self._get_perm_obj(status, role, perm_type, perm, target))
                    continue

                existing[0].permission = perm

    def add_permissions(self, status, roles, perm, targets):
        return self._update_permissions(status, roles, 'allow', perm, targets)

    def revoke_permissions(self, status, roles, perm, targets):
        return self._update_permissions(status, roles, 'disallow', perm, targets)

    def handle(self, *args, **options):
        verbosity = options.get('verbosity', 1)

        # new_visit - UNICEF can edit
        self.add_permissions(self.new_visit, self.everybody, 'view', self.everything)
        self.add_permissions(self.new_visit, self.pme, 'edit', self.visit_create)
        self.revoke_permissions(self.new_visit, self.everybody, 'view', [
            'tpmvisit.report_attachments',
            'tpmactivity.report_attachments',
            'tpmvisit.action_points',
        ])

        # draft - UNICEF can edit visit + assign
        self.add_permissions(self.draft, self.everybody, 'view', self.everything)
        self.add_permissions(self.draft, self.pme, 'edit', self.visit_create)
        self.add_permissions(self.draft, self.pme, 'action', [
            'tpmvisit.assign',
            'tpmvisit.cancel',
        ])
        self.revoke_permissions(self.draft, self.everybody, 'view', [
            'tpmvisit.report_attachments',
            'tpmactivity.report_attachments',
            'tpmvisit.action_points',
        ])

        # assigned - pme edit overview + attachments, tpm accept/reject
        self.add_permissions(self.assigned, self.everybody, 'view', self.everything)
        self.add_permissions(self.assigned, self.third_party_monitor, 'action', [
            'tpmvisit.accept',
            'tpmvisit.reject',
        ])
        self.add_permissions(self.assigned, self.pme, 'action', 'tpmvisit.cancel')
        self.revoke_permissions(self.assigned, self.everybody, 'view', [
            'tpmvisit.report_attachments',
            'tpmactivity.report_attachments',
            'tpmvisit.action_points',
        ])

        # cancelled - no edit, no actions
        self.add_permissions(self.cancelled, self.everybody, 'view', self.everything)
        self.revoke_permissions(self.cancelled, self.everybody, 'view', [
            'tpmvisit.report_attachments',
            'tpmactivity.report_attachments',
            'tpmvisit.action_points',
        ])

        # tpm_accepted - tpm edit report area, tpm can report
        self.add_permissions(self.tpm_accepted, self.everybody, 'view', self.everything)
        self.add_permissions(self.tpm_accepted, self.third_party_monitor, 'edit', [
            'tpmvisit.report_attachments',
            'tpmvisit.tpm_activities',
            'tpmactivity.report_attachments',
        ])
        self.add_permissions(self.tpm_accepted, self.third_party_monitor, 'action', 'tpmvisit.send_report')
        self.add_permissions(self.tpm_accepted, self.pme, 'action', [
            'tpmvisit.cancel',
        ])
        self.revoke_permissions(self.tpm_accepted, self.all_unicef_users, 'view', [
            'tpmvisit.report_attachments',
            'tpmactivity.report_attachments',
        ])
        self.revoke_permissions(self.tpm_accepted, self.everybody, 'view', [
            'tpmvisit.action_points',
        ])

        # tpm_rejected - pme edit overview + attachments, pme can reassign
        self.add_permissions(self.tpm_rejected, self.everybody, 'view', self.everything)
        self.add_permissions(self.tpm_rejected, self.pme, 'edit', self.visit_create)
        self.add_permissions(self.tpm_rejected, self.pme, 'action', [
            'tpmvisit.assign',
            'tpmvisit.cancel',
        ])
        self.revoke_permissions(self.tpm_rejected, self.everybody, 'view', [
            'tpmvisit.report_attachments',
            'tpmactivity.report_attachments',
        ])
        self.revoke_permissions(self.tpm_rejected, self.everybody, 'view', [
            'tpmvisit.action_points',
        ])

        # tpm_reported - UNICEF can reject report or ask actions
        self.add_permissions(self.tpm_reported, self.everybody, 'view', self.everything)
        self.add_permissions(self.tpm_reported, self.pme, 'action', [
            'tpmvisit.reject_report',
            'tpmvisit.approve',
        ])
        self.add_permissions(self.tpm_reported, [self.pme, self.focal_point], 'edit', self.follow_up_page)
        self.revoke_permissions(self.tpm_reported, self.third_party_monitor, 'view', [
            'tpmvisit.action_points',
        ])

        # tpm_report_rejected - similar to tpm_accepted. tpm edit report area, tpm can report.
        self.add_permissions(self.tpm_report_rejected, self.everybody, 'view', self.everything)
        self.add_permissions(self.tpm_report_rejected, self.third_party_monitor, 'edit', [
            'tpmvisit.report_attachments',
            'tpmvisit.tpm_activities',
            'tpmactivity.report_attachments',
        ])
        self.add_permissions(self.tpm_report_rejected, self.third_party_monitor, 'action', 'tpmvisit.send_report')
        self.revoke_permissions(self.tpm_report_rejected, self.everybody, 'view', [
            'tpmvisit.action_points',
        ])

        # unicef_approved - readonly
        self.add_permissions(self.unicef_approved, self.everybody, 'view', self.everything)
        self.revoke_permissions(self.unicef_approved, self.third_party_monitor, 'view', [
            'tpmvisit.action_points',
        ])

        # update permissions
        all_tenants = get_tenant_model().objects.exclude(schema_name='public')

        for tenant in all_tenants:
            connection.set_tenant(tenant)
            if verbosity >= 3:
                print('Using {} tenant'.format(tenant.name))

            old_permissions = TPMPermission.objects.all()
            for user in self.everybody:
                if verbosity >= 3:
                    print('Updating permissions for {}. {} -> {}'.format(
                        user,
                        len(filter(lambda p: p.user_type == self.user_roles[user], old_permissions)),
                        len(filter(lambda p: p.user_type == self.user_roles[user], self.permissions)),
                    ))

            old_permissions.delete()
            TPMPermission.objects.bulk_create(self.permissions)

        if verbosity >= 1:
            print(
                'TPM permissions was successfully updated for {}'.format(
                    ', '.join(map(lambda t: t.name, all_tenants)))
            )
