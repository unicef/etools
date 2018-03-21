from __future__ import absolute_import, division, print_function, unicode_literals

from django.core.management import BaseCommand
from django.db import connection
from django.utils import six

from tenant_schemas.utils import get_tenant_model

from audit.models import Auditor, AuditPermission, UNICEFAuditFocalPoint, UNICEFUser


class Command(BaseCommand):
    help = 'Update audit permissions'

    focal_point = 'focal_point'
    unicef_user = 'unicef_user'
    auditor = 'auditor'
    user_roles = {
        focal_point: UNICEFAuditFocalPoint.code,
        unicef_user: UNICEFUser.code,
        auditor: Auditor.code,
    }

    all_unicef_users = [focal_point, unicef_user]
    everybody = all_unicef_users + [auditor, ]

    everything = [
        'attachment.*',
        'detailedfindinginfo.*',
        'engagement.*',
        'engagementstaffmember.*',
        'financialfinding.*',
        'finding.*',
        'partnerorganization.*',
        'purchaseorder.*',
        'riskblueprint.*',
        'riskcategory.*',
        'profile.*',
        'user.*',
        'specificprocedure.*',
        'keyinternalcontrol.*'
    ]

    engagement_overview_block = [
        'engagement.agreement',
        'engagement.po_item',
        'engagement.related_agreement',
        'engagement.partner_contacted_at',
        'engagement.engagement_type',
        'engagement.start_date',
        'engagement.end_date',
        'engagement.total_value',
        'engagement.active_pd',
        'engagement.joint_audit',
        'engagement.shared_ip_with',
    ]

    partner_block = [
        'engagement.partner',
        'engagement.authorized_officers',
    ]

    staff_members_block = [
        'engagement.staff_members',
        'engagementstaffmember.*',
        'profile.*',
        'user.*',
    ]

    follow_up_page = [
        'engagement.action_points',
        'engagement.amount_refunded',
        'engagement.additional_supporting_documentation_provided',
        'engagement.explanation_for_additional_information',
        'engagement.justification_provided_and_accepted',
        'engagement.write_off_required',
        'engagement.pending_unsupported_amount',
    ]

    engagement_overview_page = engagement_overview_block + partner_block + staff_members_block

    new_engagement = 'new'
    partner_contacted = 'partner_contacted'
    report_submitted = 'report_submitted'
    final_report = 'final'
    report_cancelled = 'cancelled'

    def __init__(self, *args, **kwargs):
        super(Command, self).__init__(*args, **kwargs)
        self.permissions = []

    def _get_perm_obj(self, status, role, perm_type, perm, target):
        return AuditPermission(**{
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
                existing = [
                    p for p in self.permissions
                    if (p.instance_status == status and
                        p.target == target and
                        p.user_type == self.user_roles[role] and
                        p.permission_type == perm_type)
                ]
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

        # new status: only focal point can edit
        self.add_permissions(self.new_engagement, self.everybody, 'view', self.everything)
        self.add_permissions(self.new_engagement, self.focal_point, 'edit', self.engagement_overview_page + [
            'engagement.engagement_attachments',
            'attachment.*',
        ])
        self.add_permissions(self.new_engagement, self.focal_point, 'edit', [
            'engagement.related_agreement',
            'purchaseorder.contract_end_date',
        ])
        self.add_permissions(self.new_engagement, self.focal_point, 'edit', [
            'engagement.specific_procedures',
            'specificprocedure.description',
        ])

        # created: auditor can edit, everybody else can view, focal point can cancel
        self.add_permissions(self.partner_contacted, self.auditor, 'edit', [
            'engagement.*',
            'attachment.*',
            'detailedfindinginfo.*',
            'financialfinding.*',
            'finding.*',
            'riskblueprint.*',
            'riskcategory.*',
            'keyinternalcontrol.*'
        ])
        self.revoke_permissions(self.partner_contacted, self.auditor, 'edit',
                                self.engagement_overview_block + self.partner_block)
        self.revoke_permissions(self.partner_contacted, self.auditor, 'edit', 'engagement.engagement_attachments')
        self.add_permissions(self.partner_contacted, self.auditor, 'action', ['engagement.submit'])
        self.add_permissions(self.partner_contacted, self.auditor, 'view', [
            'purchaseorder.*',
            'partnerorganization.*',
            'engagementstaffmember.*',
            'profile.*',
            'user.*',
            'specificprocedure.*',
        ])

        self.add_permissions(self.partner_contacted, self.auditor, 'edit', [
            'specialaudit.specific_procedures',
            'specificprocedure.finding',
            'specialaudit.other_recommendations',
        ])

        self.add_permissions(self.partner_contacted, self.all_unicef_users, 'view', self.everything)
        self.add_permissions(
            self.partner_contacted, self.focal_point, 'edit', self.staff_members_block + [
                'engagement.partner',
                'engagement.partner_contacted_at',
                'engagement.authorized_officers',
                'engagement.active_pd',
                'engagement.engagement_attachments',
                'attachment.*',
            ]
        )
        self.add_permissions(self.partner_contacted, self.focal_point, 'action', 'engagement.cancel')
        self.add_permissions(self.partner_contacted, self.focal_point, 'edit', [
            'engagement.related_agreement',
            'purchaseorder.contract_end_date',
        ])

        # report submitted. focal point can finalize. all can view
        self.add_permissions(self.report_submitted, self.everybody, 'view', self.everything)
        self.add_permissions(self.report_submitted, self.focal_point, 'action', [
            'engagement.finalize',
        ])

        # final report. everybody can view. focal point can add action points
        self.add_permissions(self.final_report, self.everybody, 'view', self.everything)

        # UNICEF Focal Point can create action points
        self.add_permissions(self.final_report, self.focal_point, 'edit', self.follow_up_page)
        self.revoke_permissions(self.final_report, self.auditor, 'view', self.follow_up_page)

        # report cancelled. everybody can view
        self.add_permissions(self.report_cancelled, self.everybody, 'view', self.everything)

        # Follow-Up fields available in finalized engagements.
        for status in [self.new_engagement, self.partner_contacted, self.report_submitted, self.report_cancelled]:
            self.revoke_permissions(status, self.everybody, 'view', self.follow_up_page)

        # update permissions
        all_tenants = get_tenant_model().objects.exclude(schema_name='public')

        for tenant in all_tenants:
            connection.set_tenant(tenant)
            if verbosity >= 3:
                self.stdout.write('Using {} tenant'.format(tenant.name))

            old_permissions = AuditPermission.objects.all()
            for user in self.everybody:
                if verbosity >= 3:
                    self.stdout.write('Updating permissions for {}. {} -> {}'.format(
                        user,
                        len(filter(lambda p: p.user_type == self.user_roles[user], old_permissions)),
                        len(filter(lambda p: p.user_type == self.user_roles[user], self.permissions)),
                    ))

            old_permissions.delete()
            AuditPermission.objects.bulk_create(self.permissions)

        if verbosity >= 1:
            self.stdout.write(
                'Audit permissions was successfully updated for {}'.format(
                    ', '.join(map(lambda t: t.name, all_tenants)))
            )
