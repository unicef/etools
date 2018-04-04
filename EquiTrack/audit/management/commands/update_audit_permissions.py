from __future__ import absolute_import, division, print_function, unicode_literals

from django.core.management import BaseCommand
from django.db.models import Q
from django.utils import six

from audit.conditions import AuditStaffMemberCondition, AuditModuleCondition
from audit.models import Auditor, UNICEFAuditFocalPoint, UNICEFUser, Engagement
from permissions2.conditions import GroupCondition, ObjectStatusCondition, NewObjectCondition
from permissions2.models import Permission


class Command(BaseCommand):
    help = 'Update audit permissions'

    focal_point = 'focal_point'
    unicef_user = 'unicef_user'
    auditor = 'auditor'
    user_roles = {
        focal_point: [GroupCondition.predicate_template.format(group=UNICEFAuditFocalPoint.name)],
        unicef_user: [GroupCondition.predicate_template.format(group=UNICEFUser.name)],
        auditor: [GroupCondition.predicate_template.format(group=Auditor.name),
                  AuditStaffMemberCondition.predicate]
    }

    all_unicef_users = [focal_point, unicef_user]
    everybody = all_unicef_users + [auditor, ]

    engagement_overview_read_block = [
        'audit.engagement.unique_id',

        'audit.engagement.status',
        'audit.engagement.status_date',

        'purchase_order.purchaseorder.*',
        'purchase_order.auditorfirm.*',
    ]

    engagement_overview_editable_block = [
        'audit.engagement.agreement',
        'audit.engagement.po_item',
        'audit.engagement.partner_contacted_at',
        'audit.engagement.engagement_type',
        'audit.engagement.start_date',
        'audit.engagement.end_date',
        'audit.engagement.total_value',
        'audit.engagement.joint_audit',
        'audit.engagement.shared_ip_with',
        'audit.engagement.exchange_rate',
        'audit.engagement.related_agreement',
        'purchase_order.purchaseorder.contract_end_date',
    ]

    engagement_status_editable_date_fields = [
        'audit.engagement.date_of_comments_by_ip',
        'audit.engagement.date_of_comments_by_unicef',
        'audit.engagement.date_of_draft_report_to_ip',
        'audit.engagement.date_of_draft_report_to_unicef',
        'audit.engagement.date_of_field_visit',
    ]
    engagement_status_auto_date_fields = [
        'audit.engagement.created',
        'audit.engagement.date_of_cancel',
        'audit.engagement.date_of_final_report',
        'audit.engagement.date_of_report_submit',
    ]

    special_audit_block = [
        'audit.engagement.specific_procedures',
    ]

    partner_block = [
        'audit.engagement.partner',
        'audit.engagement.authorized_officers',
        'audit.engagement.active_pd',
    ]

    staff_members_block = [
        'audit.engagement.staff_members',
    ]

    follow_up_page = [
        # 'audit.engagement.action_points',
        # 'audit.engagement.amount_refunded',
        # 'audit.engagement.additional_supporting_documentation_provided',
        # 'audit.engagement.explanation_for_additional_information',
        # 'audit.engagement.justification_provided_and_accepted',
        # 'audit.engagement.write_off_required',
        # 'audit.engagement.pending_unsupported_amount',
    ]

    engagement_overview_editable_page = engagement_overview_editable_block + special_audit_block + partner_block + staff_members_block
    engagement_overview_page = engagement_overview_editable_page + engagement_overview_read_block
    engagement_attachments_block = [
        'audit.engagement.engagement_attachments',
    ]
    report_attachments_block = [
        # 'audit.engagement.report_attachments',
    ]

    microassessment_report_fields = [
        # 'audit.engagement.overall_risk_assessment',
        # 'audit.engagement.questionnaire',
        # 'audit.engagement.test_subject_areas',
    ]

    def _update_permissions(self, role, perm, targets, perm_type, condition=None):
        if isinstance(role, (list, tuple)):
            for r in role:
                self._update_permissions(r, perm, targets, perm_type, condition)
            return

        if isinstance(targets, six.string_types):
            targets = [targets]

        conditions = [AuditModuleCondition()]

        if condition is not None:
            conditions = condition[:]

        conditions.extend(self.user_roles[role])

        if self.verbosity >= 3:
            for target in targets:
                print(
                    '   {} {} permission for {} on {}\n'
                    '      if {}.'.format(
                        'Add' if perm_type == 'allow' else 'Revoke',
                        perm,
                        role,
                        target,
                        conditions,
                    )
                )

        self.permissions.extend([
            Permission(target=target, permission=perm, permission_type=perm_type, condition=conditions)
            for target in targets
        ])

    def add_permission(self, role, perm, targets, condition=None):
        self._update_permissions(role, perm, targets, 'allow', condition)

    def revoke_permission(self, role, perm, targets, condition=None):
        self._update_permissions(role, perm, targets, 'disallow', condition)

    def engagement_status(self, status):
        obj = '{}_{}'.format(Engagement._meta.app_label, Engagement._meta.model_name)
        return [ObjectStatusCondition.predicate_template.format(obj=obj, status=status)]

    def new_engagement(self):
        model = '{}_{}'.format(Engagement._meta.app_label, Engagement._meta.model_name)
        return [NewObjectCondition.predicate_template.format(model=model)]

    def handle(self, *args, **options):
        self.verbosity = options.get('verbosity', 1)

        self.permissions = []

        if self.verbosity >= 2:
            print(
                'Generating new permissions...'
            )

        # common permissions: unicef users can view everything, auditor can view everything except follow up
        self.add_permission([self.focal_point, self.auditor], 'edit', [
            'purchase_order.auditorfirm.staff_members',
            'purchase_order.auditorstaffmember.*',
        ])

        self.add_permission(
            self.everybody, 'view',
            self.engagement_overview_page +
            self.engagement_status_auto_date_fields +
            self.engagement_status_editable_date_fields +
            self.engagement_attachments_block
        )

        # new object: focal point can add
        self.add_permission(
            self.focal_point, 'edit',
            self.engagement_overview_editable_page + self.engagement_attachments_block,
            condition=self.new_engagement()
        )

        # ip_contacted: auditor can edit, everybody else can view, focal point can cancel and edit staff members
        # self.add_permission(self.auditor, 'edit', self.staff_members_block + self.report_attachments_block + self.engagement_status_editable_date_fields, condition=self.engagement_status(Engagement.STATUSES.partner_contacted))

        self.add_permission(
            self.focal_point, 'edit',
            self.staff_members_block,
            condition=self.engagement_status(Engagement.STATUSES.partner_contacted)
        )
        self.add_permission(
            self.focal_point, 'action',
            'audit.engagement.cancel',
            condition=self.engagement_status(Engagement.STATUSES.partner_contacted)
        )

        # self.add_permissions(self.partner_contacted, self.auditor, 'edit', [
        #     'engagement.*',
        #     'attachment.*',
        #     'detailedfindinginfo.*',
        #     'financialfinding.*',
        #     'finding.*',
        #     'riskblueprint.*',
        #     'riskcategory.*',
        #     'keyinternalcontrol.*'
        # ])
        # self.revoke_permissions(self.partner_contacted, self.auditor, 'edit',
        #                         self.engagement_overview_block + self.partner_block)
        # self.revoke_permissions(self.partner_contacted, self.auditor, 'edit', 'engagement.engagement_attachments')
        # self.add_permissions(self.partner_contacted, self.auditor, 'action', ['engagement.submit'])
        # self.add_permissions(self.partner_contacted, self.auditor, 'view', [
        #     'purchaseorder.*',
        #     'partnerorganization.*',
        #     'engagementstaffmember.*',
        #     'profile.*',
        #     'user.*',
        #     'specificprocedure.*',
        # ])
        #
        # self.add_permissions(self.partner_contacted, self.auditor, 'edit', [
        #     'specialaudit.specific_procedures',
        #     'specificprocedure.finding',
        #     'specialaudit.other_recommendations',
        # ])
        #
        # self.add_permissions(self.partner_contacted, self.all_unicef_users, 'view', self.everything)
        # self.add_permissions(
        #     self.partner_contacted, self.focal_point, 'edit', self.staff_members_block + [
        #         'engagement.partner',
        #         'engagement.partner_contacted_at',
        #         'engagement.authorized_officers',
        #         'engagement.active_pd',
        #         'engagement.engagement_attachments',
        #         'attachment.*',
        #     ]
        # )
        # self.add_permissions(self.partner_contacted, self.focal_point, 'action', 'engagement.cancel')
        # self.add_permissions(self.partner_contacted, self.focal_point, 'edit', [
        #     'engagement.related_agreement',
        #     'purchaseorder.contract_end_date',
        # ])
        #
        # # report submitted. focal point can finalize. all can view
        # self.add_permissions(self.report_submitted, self.everybody, 'view', self.everything)
        # self.add_permissions(self.report_submitted, self.focal_point, 'action', [
        #     'engagement.finalize',
        # ])
        #
        # # final report. everybody can view. focal point can add action points
        # self.add_permissions(self.final_report, self.everybody, 'view', self.everything)
        #
        # # UNICEF Focal Point can create action points
        # self.add_permissions(self.final_report, self.focal_point, 'edit', self.follow_up_page)
        # self.revoke_permissions(self.final_report, self.auditor, 'view', self.follow_up_page)
        #
        # # report cancelled. everybody can view
        # self.add_permissions(self.report_cancelled, self.everybody, 'view', self.everything)
        #
        # # Follow-Up fields available in finalized engagements.
        # for status in [self.new_engagement, self.partner_contacted, self.report_submitted, self.report_cancelled]:
        #     self.revoke_permissions(status, self.everybody, 'view', self.follow_up_page)

        old_permissions = Permission.objects.filter(
            Q(target__startswith='audit.') |
            Q(target__startswith='purchase_order.')
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
                'Audit permissions updated ({}) -> ({}).'.format(old_permissions_count, len(self.permissions))
            )
