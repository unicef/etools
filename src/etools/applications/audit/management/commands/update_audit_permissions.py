from django.core.management import BaseCommand
from django.db.models import Q

from etools.applications.action_points.conditions import (
    ActionPointAssignedByCondition,
    ActionPointAssigneeCondition,
    ActionPointAuthorCondition,
)
from etools.applications.action_points.models import ActionPoint
from etools.applications.audit.conditions import (
    AuditModuleCondition,
    AuditStaffMemberCondition,
    EngagementStaffMemberCondition,
    EngagementUnicefCommentsReceivedCondition,
    IsUnicefUserCondition,
)
from etools.applications.audit.models import (
    Auditor,
    Engagement,
    EngagementActionPoint,
    UNICEFAuditFocalPoint,
    UNICEFUser,
)
from etools.applications.permissions2.conditions import GroupCondition, NewObjectCondition, ObjectStatusCondition
from etools.applications.permissions2.models import Permission
from etools.applications.permissions2.utils import get_model_target


class Command(BaseCommand):
    help = 'Update audit permissions'

    focal_point = 'focal_point'
    unicef_user = 'unicef_user'
    auditor = 'auditor'
    engagement_staff_auditor = 'engagement_staff_auditor'

    action_point_author = 'action_point_author'
    action_point_assignee = 'action_point_assignee'
    action_point_assigned_by = 'action_point_assigned_by'

    user_roles = {
        focal_point: [GroupCondition.predicate_template.format(group=UNICEFAuditFocalPoint.name)],
        unicef_user: [GroupCondition.predicate_template.format(group=UNICEFUser.name)],
        auditor: [GroupCondition.predicate_template.format(group=Auditor.name),
                  AuditStaffMemberCondition.predicate],
        engagement_staff_auditor: [GroupCondition.predicate_template.format(group=Auditor.name),
                                   AuditStaffMemberCondition.predicate,
                                   EngagementStaffMemberCondition.predicate],

        action_point_author: [ActionPointAuthorCondition.predicate],
        action_point_assignee: [ActionPointAssigneeCondition.predicate],
        action_point_assigned_by: [ActionPointAssignedByCondition.predicate],
    }

    all_unicef_users = [focal_point, unicef_user]
    everybody = all_unicef_users + [auditor, ]
    action_points_editors = [focal_point, action_point_author, action_point_assignee, action_point_assigned_by]

    engagement_overview_read_block = [
        'audit.engagement.reference_number',

        'audit.engagement.status',
        'audit.engagement.status_date',
        'audit.engagement.exchange_rate',

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
        'audit.engagement.total_value_local',
        'audit.engagement.joint_audit',
        'audit.engagement.year_of_audit',
        'audit.engagement.shared_ip_with',
        'audit.engagement.related_agreement',
        'audit.engagement.sections',
        'audit.engagement.offices',
        'audit.engagement.face_forms',
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

    users_notified_block = [
        'audit.engagement.users_notified'
    ]

    action_points_block = [
        'audit.engagement.action_points',
        'audit.engagementactionpoint.*',
    ]

    follow_up_editable_page = [
        'audit.engagement.amount_refunded_local',
        'audit.engagement.additional_supporting_documentation_provided_local',
        'audit.engagement.justification_provided_and_accepted_local',
        'audit.engagement.write_off_required_local',
        'audit.engagement.pending_unsupported_amount',
        'audit.engagement.pending_unsupported_amount_local',
        'audit.engagement.explanation_for_additional_information',
    ]

    follow_up_page = follow_up_editable_page + [
        'audit.spotcheck.total_amount_tested',
        'audit.spotcheck.total_amount_of_ineligible_expenditure',
        'audit.spotcheck.total_amount_tested_local',
        'audit.spotcheck.total_amount_of_ineligible_expenditure_local',
    ]

    engagement_overview_editable_page = (engagement_overview_editable_block + special_audit_block +
                                         partner_block + staff_members_block + users_notified_block)

    engagement_overview_page = engagement_overview_editable_page + engagement_overview_read_block

    engagement_attachments_block = [
        'audit.engagement.engagement_attachments',
    ]
    report_attachments_block = [
        'audit.engagement.report_attachments',
    ]

    microassessment_report_block = [
        'audit.microassessment.overall_risk_assessment',
        'audit.microassessment.questionnaire',
        'audit.microassessment.test_subject_areas',
        'audit.microassessment.findings',
    ]

    audit_report_block = [
        'audit.audit.audit_opinion',
        'audit.audit.audited_expenditure_local',
        'audit.audit.financial_finding_set',
        'audit.audit.key_internal_controls',
        'audit.audit.key_internal_weakness',
        'audit.audit.currency_of_report',
    ]

    spot_check_report_block = [
        'audit.spotcheck.findings',
        'audit.spotcheck.financial_finding_set',
        'audit.spotcheck.internal_controls',
        'audit.spotcheck.total_amount_tested_local',
        'audit.spotcheck.currency_of_report',
    ]

    special_audit_report_block = [
        'audit.specialaudit.other_recommendations',
        'audit.specialaudit.specific_procedures',
    ]

    report_readonly_block = [
        'audit.engagement.amount_refunded',
        'audit.engagement.additional_supporting_documentation_provided',
        'audit.engagement.justification_provided_and_accepted',
        'audit.engagement.write_off_required',
        'audit.audit.audited_expenditure',
        'audit.audit.percent_of_audited_expenditure',
        'audit.audit.number_of_financial_findings',
        'audit.audit.pending_unsupported_amount',
        'audit.audit.pending_unsupported_amount_local',
        'audit.audit.financial_findings',
        'audit.audit.financial_findings_local',
        'audit.spotcheck.total_amount_of_ineligible_expenditure',
        'audit.spotcheck.total_amount_of_ineligible_expenditure_local',
        'audit.spotcheck.total_amount_tested',
        'audit.spotcheck.percent_of_audited_expenditure'
    ]

    report_editable_block = (microassessment_report_block + audit_report_block + spot_check_report_block +
                             special_audit_report_block + report_attachments_block)

    report_block = report_readonly_block + report_editable_block

    def _update_permissions(self, role, perm, targets, perm_type, condition=None):
        if isinstance(role, (list, tuple)):
            for r in role:
                self._update_permissions(r, perm, targets, perm_type, condition)
            return

        if isinstance(targets, str):
            targets = [targets]

        condition = (condition or []) + [AuditModuleCondition()] + self.user_roles[role]

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

    def engagement_status(self, status):
        obj = get_model_target(Engagement)
        return [ObjectStatusCondition.predicate_template.format(obj=obj, status=status)]

    def engagement_comments_received_by_unicef(self):
        return [EngagementUnicefCommentsReceivedCondition.predicate]

    def new_engagement(self):
        model = get_model_target(Engagement)
        return [NewObjectCondition.predicate_template.format(model=model)]

    def new_action_point(self):
        model = get_model_target(EngagementActionPoint)
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
        Permission.objects.bulk_create(self.defined_permissions)

        if self.verbosity >= 1:
            self.stdout.write(
                'Audit permissions updated ({}) -> ({}).'.format(old_permissions_count, len(self.defined_permissions))
            )

    def assign_permissions(self):
        # common permissions: unicef users can view everything, auditor can view everything except follow up
        self.add_permissions(
            self.everybody, 'view',
            self.engagement_overview_page +
            self.engagement_status_auto_date_fields +
            self.engagement_status_editable_date_fields +
            self.engagement_attachments_block +
            self.report_editable_block
        )

        self.add_permissions([self.focal_point, self.auditor], 'edit', self.engagement_attachments_block)

        self.add_permissions(self.focal_point, 'edit', [
            'purchase_order.purchaseorder.contract_end_date',
        ] + self.report_attachments_block)

        # new object: focal point can add
        self.add_permissions(
            self.focal_point, 'edit',
            self.engagement_overview_editable_page,
            condition=self.new_engagement()
        )

        # cancelled engagement
        cancelled_condition = self.engagement_status(Engagement.STATUSES.cancelled)
        self.add_permissions(
            self.everybody, 'view',
            'audit.engagement.cancel_comment',
            condition=cancelled_condition
        )

        # ip_contacted: auditor can edit, everybody else can view, focal point can cancel and edit staff members
        partner_contacted_condition = self.engagement_status(Engagement.STATUSES.partner_contacted)
        self.add_permissions(self.auditor, 'edit', self.report_attachments_block, condition=partner_contacted_condition)
        self.add_permissions(
            self.engagement_staff_auditor, 'view',
            self.report_readonly_block,
            condition=partner_contacted_condition
        )
        is_unicef_user = [IsUnicefUserCondition.predicate]
        self.add_permissions(
            self.engagement_staff_auditor, 'edit',
            self.users_notified_block,
            condition=partner_contacted_condition + is_unicef_user
        )
        self.add_permissions(
            self.engagement_staff_auditor, 'edit',
            self.staff_members_block +
            self.engagement_status_editable_date_fields +
            self.report_editable_block,
            condition=partner_contacted_condition
        )
        self.add_permissions(
            self.engagement_staff_auditor, 'action',
            'audit.engagement.submit',
            condition=partner_contacted_condition
        )

        self.add_permissions(
            self.focal_point, 'edit',
            self.staff_members_block +
            self.users_notified_block,
            condition=partner_contacted_condition
        )
        self.add_permissions(
            self.focal_point, 'action',
            'audit.engagement.cancel',
            condition=partner_contacted_condition
        )
        self.add_permissions(
            self.everybody, 'view',
            'audit.engagement.send_back_comment',
            condition=partner_contacted_condition
        )

        # report submitted. focal point can finalize or send back. all can view
        report_submitted_condition = self.engagement_status(Engagement.STATUSES.report_submitted)
        self.add_permissions(self.auditor, 'edit', self.report_attachments_block, condition=report_submitted_condition)
        self.add_permissions(
            self.focal_point, 'action',
            'audit.engagement.finalize',
            condition=report_submitted_condition
        )
        self.add_permissions(
            self.focal_point, 'action',
            'audit.engagement.send_back',
            condition=report_submitted_condition
        )
        self.add_permissions(
            self.everybody, 'view',
            self.report_block,
            condition=report_submitted_condition
        )
        self.add_permissions(
            self.everybody, 'view',
            'audit.engagement.send_back_comment',
            condition=report_submitted_condition
        )

        # final report. everybody can view. focal point can add action points
        final_engagement_condition = self.engagement_status(Engagement.STATUSES.final)
        self.add_permissions(
            self.everybody, 'view',
            self.report_block,
            condition=final_engagement_condition
        )
        self.add_permissions(
            self.all_unicef_users, 'view',
            self.follow_up_page,
            condition=self.engagement_comments_received_by_unicef()
        )
        self.add_permissions(
            self.all_unicef_users, 'view',
            self.action_points_block,
            condition=self.engagement_comments_received_by_unicef()
        )
        self.add_permissions(
            self.focal_point, 'edit',
            self.follow_up_editable_page,
            condition=self.engagement_comments_received_by_unicef()
        )

        # action points related permissions. editable by focal point, author, assignee and assigner
        opened_action_point_condition = self.action_point_status(EngagementActionPoint.STATUSES.open)

        self.add_permissions(
            self.all_unicef_users,
            'edit',
            'audit.engagement.action_points',
            condition=self.engagement_comments_received_by_unicef()
        )
        self.add_permissions(
            self.all_unicef_users,
            'edit',
            'audit.engagementactionpoint.*',
            condition=self.engagement_comments_received_by_unicef() + self.new_action_point(),
        )
        self.add_permissions(
            self.action_points_editors, 'edit',
            self.action_points_block,
            condition=opened_action_point_condition
        )
        self.add_permissions(
            [self.focal_point, self.action_point_assignee], 'action',
            'audit.engagementactionpoint.complete',
            condition=opened_action_point_condition
        )
