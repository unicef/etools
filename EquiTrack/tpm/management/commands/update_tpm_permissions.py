from django.core.management import BaseCommand
from django.db import connection
from django.utils import six

from tenant_schemas import get_tenant_model

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
    ]

    visit_create = [
        'tpmvisit.tpm_partner',
        'tpmvisit.tpm_activities',
        'tpmvisit.attachments',
        'tpmvisit.unicef_focal_points',
        'tpmvisit.sections',
        'tpmactivity.*',
    ]

    follow_up_page = [
        'tpmvisit.tmp_activities',
        'tpmactivity.action_points',
        'tpmactivityactionpoint.*',
    ]

    new_visit = 'new'
    draft = 'draft'
    assigned = 'assigned'
    tpm_accepted = 'tpm_accepted'
    tpm_rejected = 'tpm_rejected'
    tpm_reported = 'tpm_reported'
    submitted = 'submitted'
    unicef_approved = 'unicef_approved'
    tpm_report_rejected = 'tpm_report_rejected'
    cancelled = 'cancelled'

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

        # all users can view  visit on all steps
        self.add_permissions(self.new_visit, self.everybody, 'view', self.everything)
        self.add_permissions(self.draft, self.everybody, 'view', self.everything)
        self.add_permissions(self.assigned, self.everybody, 'view', self.everything)
        self.add_permissions(self.tpm_accepted, self.everybody, 'view', self.everything)
        self.add_permissions(self.tpm_rejected, self.everybody, 'view', self.everything)
        self.add_permissions(self.tpm_reported, self.everybody, 'view', self.everything)
        self.add_permissions(self.submitted, self.everybody, 'view', self.everything)
        self.add_permissions(self.unicef_approved, self.everybody, 'view', self.everything)

        # new status: only pme can edit
        self.add_permissions(self.new_visit, self.pme, 'edit', self.visit_create)

        # pme can edit visit before submit
        self.add_permissions(self.draft, self.pme, 'edit', self.visit_create)
        self.add_permissions(self.draft, self.pme, 'action', ['tpmvisit.assign'])
        self.add_permissions(self.draft, self.pme, 'action', ['tpmvisit.cancel'])

        # TPM can accept or reject visit and add reject comment
        self.add_permissions(self.assigned, self.third_party_monitor, 'action', ['tpmvisit.accept', 'tpmvisit.reject'])

        # TPM can add report
        self.add_permissions(self.tpm_accepted, self.third_party_monitor, 'edit', ['tpmvisit.report'])
        self.add_permissions(self.tpm_accepted, self.third_party_monitor, 'action', ['tpmvisit.send_report'])
        self.add_permissions(self.tpm_report_rejected, self.third_party_monitor, 'edit', ['tpmvisit.report'])
        self.add_permissions(self.tpm_report_rejected, self.third_party_monitor, 'action', ['tpmvisit.send_report'])

        # UNICEF can reject report or ask actions
        self.add_permissions(self.tpm_reported, [self.pme, self.focal_point], 'action', ['tpmvisit.reject_report'])

        # UNICEF can approve report or ask actions
        self.add_permissions(self.tpm_reported, [self.pme, self.focal_point], 'action', ['tpmvisit.approve'])

        # UNICEF and PME can add action point for approved visit
        self.add_permissions(self.unicef_approved, [self.pme, self.focal_point], 'edit', self.follow_up_page)

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
