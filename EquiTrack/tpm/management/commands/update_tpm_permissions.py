from django.core.management import BaseCommand
from django.utils import six

from tpm.models import TPMPermission, UNICEFFocalPoint, UNICEFUser, PME, ThirdPartyMonitor


class Command(BaseCommand):
    help = 'Clean audit permissions'

    focal_point = 'focal_point'
    unicef_user = 'unicef_user'
    pme = 'pme'
    third_party_monitor = 'third_party_monitor'
    user_roles = {
        focal_point: UNICEFFocalPoint.code,
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
        'tpmsectorcovered.*',
        'tpmlowresult.*',
        'tpmlocation.*',
        'tpmvisitreport.*',
    ]

    visit_create = [
        'tpmvisit.tpm_partner',
        'tpmvisit.visit_start',
        'tpmvisit.visit_end',
        'tpmvisit.unicef_focal_points',
        'tpmvisit.attachments',
        'tpmactivity.*',
        'tpmsectorcovered.*',
        'tpmlowresult.*',
        'tpmlocation.*',
    ]

    new_visit = 'new'
    draft = 'draft'
    submitted = 'submitted'
    tpm_accepted = 'tpm_accepted'
    tpm_rejected = 'tpm_rejected'
    tpm_reported = 'tpm_reported'
    tpm_action_required = 'tpm_action_required'
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
                    lambda p: p.instance_status == status and
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
        # all users can view  visit on all steps
        self.add_permissions(self.new_visit, self.everybody, 'view', self.everything)
        self.add_permissions(self.draft, self.everybody, 'view', self.everything)
        self.add_permissions(self.tpm_accepted, self.everybody, 'view', self.everything)
        self.add_permissions(self.tpm_rejected, self.everybody, 'view', self.everything)
        self.add_permissions(self.tpm_reported, self.everybody, 'view', self.everything)
        self.add_permissions(self.tpm_action_required, self.everybody, 'view', self.everything)

        # new status: only pme can edit
        self.add_permissions(self.new_visit, self.pme, 'edit', self.visit_create)

        # pme can edit visit before submit
        self.add_permissions(self.new_visit, self.pme, 'edit', self.visit_create)
        self.add_permissions(self.draft, self.pme, 'action', ['tpmvisit.submit'])

        # TPM can accept or reject visit and add reject comment
        self.add_permissions(self.submitted, self.third_party_monitor, 'action', ['tpmvisit.accept', 'tpmvisit.reject'])
        self.add_permissions(self.tpm_rejected, self.third_party_monitor, 'edit', ['tpmvisit.reject_comment'])

        # TPM can add report
        self.add_permissions(self.tpm_accepted, self.third_party_monitor, 'edit', ['tpmvisit.tpm_report', 'tpmreport.*'])
        self.add_permissions(self.tpm_accepted, self.third_party_monitor, 'action', ['tpmvisit.report', ])

        # UNICEF can approve report or ask actions
        self.add_permissions(self.tpm_reported, [self.pme, self.focal_point], 'action', ['tpmvisit.approve', ])
        self.add_permissions(self.tpm_reported, [self.pme, self.focal_point], 'action', ['tpmvisit.action_required', ])
        self.add_permissions(self.unicef_approved, [self.pme, self.focal_point], 'edit', ['tpmvisit.tpm_report', 'tpmreport.recommendations'])

        # update permissions
        TPMPermission.objects.all().delete()
        print('{} objects created.'.format(
            len(TPMPermission.objects.bulk_create(self.permissions))
        ))
