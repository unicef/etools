
import itertools

from django.conf import settings
from django.contrib.contenttypes.fields import GenericRelation
from django.db import models
from django.utils import six, timezone
from django.utils.encoding import force_text, python_2_unicode_compatible
from django.utils.translation import ugettext_lazy as _

from django_fsm import FSMField, transition
from model_utils import Choices, FieldTracker
from model_utils.models import TimeStampedModel

from etools.applications.activities.models import Activity
from etools.applications.attachments.models import Attachment
from etools.applications.EquiTrack.utils import get_environment
from etools.applications.notification.utils import send_notification_using_email_template
from etools.applications.publics.models import SoftDeleteMixin
from etools.applications.tpm.tpmpartners.models import TPMPartner, TPMPartnerStaffMember
from etools.applications.tpm.transitions.conditions import (TPMVisitAssignRequiredFieldsCheck,
                                                            TPMVisitReportValidations, ValidateTPMVisitActivities,)
from etools.applications.tpm.transitions.serializers import (TPMVisitApproveSerializer, TPMVisitCancelSerializer,
                                                             TPMVisitRejectSerializer,)
from etools.applications.utils.common.models.fields import CodedGenericRelation
from etools.applications.utils.common.urlresolvers import build_frontend_url
from etools.applications.utils.groups.wrappers import GroupWrapper
from etools.applications.utils.permissions.models.models import StatusBasePermission
from etools.applications.utils.permissions.models.query import StatusBasePermissionQueryset
from etools.applications.utils.permissions.utils import has_action_permission


def _has_action_permission(action):
    return lambda instance=None, user=None: \
        has_action_permission(TPMPermission, instance=instance, user=user, action=action)


@python_2_unicode_compatible
class TPMVisit(SoftDeleteMixin, TimeStampedModel, models.Model):

    DRAFT = 'draft'
    ASSIGNED = 'assigned'
    CANCELLED = 'cancelled'
    ACCEPTED = 'tpm_accepted'
    REJECTED = 'tpm_rejected'
    REPORTED = 'tpm_reported'
    REPORT_REJECTED = 'tpm_report_rejected'
    UNICEF_APPROVED = 'unicef_approved'

    STATUSES = Choices(
        (DRAFT, _('Draft')),
        (ASSIGNED, _('Assigned')),
        (CANCELLED, _('Cancelled')),
        (ACCEPTED, _('TPM Accepted')),
        (REJECTED, _('TPM Rejected')),
        (REPORTED, _('TPM Reported')),
        (REPORT_REJECTED, _('Sent Back to TPM')),
        (UNICEF_APPROVED, _('UNICEF Approved')),
    )

    STATUSES_DATES = {
        STATUSES.draft: 'date_created',
        STATUSES.assigned: 'date_of_assigned',
        STATUSES.cancelled: 'date_of_cancelled',
        STATUSES.tpm_accepted: 'date_of_tpm_accepted',
        STATUSES.tpm_rejected: 'date_of_tpm_rejected',
        STATUSES.tpm_reported: 'date_of_tpm_reported',
        STATUSES.tpm_report_rejected: 'date_of_tpm_report_rejected',
        STATUSES.unicef_approved: 'date_of_unicef_approved',
    }

    tpm_partner = models.ForeignKey(
        TPMPartner, verbose_name=_('TPM Vendor'), null=True,
        on_delete=models.CASCADE,
    )

    status = FSMField(verbose_name=_('Status'), max_length=20,
                      choices=STATUSES, default=STATUSES.draft, protected=True)

    # UNICEF cancelled visit
    cancel_comment = models.TextField(verbose_name=_('Cancel Comment'), blank=True)
    # TPM rejected visit
    reject_comment = models.TextField(verbose_name=_('Reason for Rejection'), blank=True)
    approval_comment = models.TextField(verbose_name=_('Approval Comments'), blank=True)

    report_attachments = GenericRelation(Attachment, verbose_name=_('Visit Report'), blank=True)

    visit_information = models.TextField(verbose_name=_('Visit Information'), blank=True)

    date_of_assigned = models.DateField(blank=True, null=True, verbose_name=_('Date of Assigned'))
    date_of_cancelled = models.DateField(blank=True, null=True, verbose_name=_('Date of Cancelled'))
    date_of_tpm_accepted = models.DateField(blank=True, null=True, verbose_name=_('Date of TPM Accepted'))
    date_of_tpm_rejected = models.DateField(blank=True, null=True, verbose_name=_('Date of TPM Rejected'))
    date_of_tpm_reported = models.DateField(blank=True, null=True, verbose_name=_('Date of TPM Reported'))
    date_of_tpm_report_rejected = models.DateField(blank=True, null=True, verbose_name=_('Date of Sent Back to TPM'))
    date_of_unicef_approved = models.DateField(blank=True, null=True, verbose_name=_('Date of UNICEF Approved'))

    tpm_partner_focal_points = models.ManyToManyField(
        TPMPartnerStaffMember, verbose_name=_('TPM Focal Points'), related_name='tpm_visits', blank=True
    )

    tpm_partner_tracker = FieldTracker(fields=['tpm_partner', ])

    class Meta:
        ordering = ('id',)
        verbose_name = _('TPM Visit')
        verbose_name_plural = _('TPM Visits')

    @property
    def date_created(self):
        return self.created.date()

    @property
    def status_date(self):
        return getattr(self, self.STATUSES_DATES[self.status])

    @property
    def reference_number(self):
        return '{0}/{1}/TPM'.format(
            self.created.year,
            self.id,
        )

    @property
    def start_date(self):
        # TODO: Rewrite to reduce number of SQL queries.
        return self.tpm_activities.aggregate(
            models.Min('date'))['date__min']

    @property
    def end_date(self):
        # TODO: Rewrite to reduce number of SQL queries.
        return self.tpm_activities.aggregate(
            models.Max('date'))['date__max']

    @property
    def unicef_focal_points(self):
        return set(itertools.chain(*map(
            lambda a: a.unicef_focal_points.all(),
            self.tpm_activities.all()
        )))

    @property
    def unicef_focal_points_with_emails(self):
        return list(filter(lambda u: u.email and u.is_active, self.unicef_focal_points))

    def __str__(self):
        return 'Visit ({} to {} at {} - {})'.format(
            self.tpm_partner, ', '.join(filter(
                lambda x: x,
                self.tpm_activities.values_list('partner__name', flat=True)
            )),
            self.start_date, self.end_date
        )

    def has_action_permission(self, user=None, action=None):
        return _has_action_permission(self, user, action)

    def get_mail_context(self, user=None):
        object_url = self.get_object_url()

        if user:
            from etools.applications.email_auth.utils import update_url_with_auth_token
            object_url = update_url_with_auth_token(object_url, user)

        activities = self.tpm_activities.all()
        interventions = set(a.intervention.title for a in activities if a.intervention)
        partner_names = set(a.partner.name for a in activities)
        return {
            'reference_number': self.reference_number,
            'tpm_partner': self.tpm_partner.name if self.tpm_partner else '-',
            'tpm_activities': [a.get_mail_context() for a in activities],
            'multiple_tpm_activities': activities.count() > 1,
            'object_url': object_url,
            'partners': ', '.join(partner_names),
            'interventions': ', '.join(interventions),
        }

    def _send_email(self, recipients, template_name, context=None, user=None, **kwargs):
        context = context or {}

        base_context = {
            'visit': self.get_mail_context(user=user),
            'environment': get_environment(),
        }
        base_context.update(context)
        context = base_context

        if isinstance(recipients, six.string_types):
            recipients = [recipients, ]
        else:
            recipients = list(recipients)

        # assert recipients
        if recipients:
            send_notification_using_email_template(
                recipients=recipients,
                email_template_name=template_name,
                context=context,
            )

    def _get_unicef_focal_points_as_email_recipients(self):
        return list(map(lambda u: u.email, self.unicef_focal_points_with_emails))

    def _get_tpm_focal_points_as_email_recipients(self):
        return list(
            self.tpm_partner_focal_points.filter(
                user__email__isnull=False,
                user__is_active=True
            ).values_list('user__email', flat=True)
        )

    def _get_ip_focal_points_as_email_recipients(self):
        return list(
            self.tpm_activities.filter(
                intervention__partner_focal_points__email__isnull=False
            ).values_list('intervention__partner_focal_points__email', flat=True)
        )

    @transition(
        status, source=[STATUSES.draft, STATUSES.tpm_rejected], target=STATUSES.assigned,
        conditions=[
            TPMVisitAssignRequiredFieldsCheck.as_condition(),
            ValidateTPMVisitActivities.as_condition(),
        ],
        permission=_has_action_permission(action='assign'),
        custom={
            'name': lambda obj: _('Re-assign') if obj.status == TPMVisit.STATUSES.tpm_rejected else _('Assign')
        }
    )
    def assign(self):
        self.date_of_assigned = timezone.now()

        if self.tpm_partner.email:
            self._send_email(
                self.tpm_partner.email, 'tpm/visit/assign',
                cc=self._get_unicef_focal_points_as_email_recipients()
            )

        for staff_member in self.tpm_partner_focal_points.filter(user__email__isnull=False, user__is_active=True):
            self._send_email(
                staff_member.user.email, 'tpm/visit/assign_staff_member',
                context={'recipient': staff_member.user.get_full_name()},
                user=staff_member.user
            )

    @transition(
        status, source=[
            STATUSES.draft, STATUSES.assigned, STATUSES.tpm_accepted, STATUSES.tpm_rejected,
            STATUSES.tpm_reported, STATUSES.tpm_report_rejected,
        ], target=STATUSES.cancelled, permission=_has_action_permission(action='cancel'),
        custom={
            'serializer': TPMVisitCancelSerializer,
            'name': _('Cancel Visit')
        }
    )
    def cancel(self, cancel_comment):
        self.cancel_comment = cancel_comment
        self.date_of_cancelled = timezone.now()

    @transition(status, source=[STATUSES.assigned], target=STATUSES.tpm_rejected,
                permission=_has_action_permission(action='reject'),
                custom={'serializer': TPMVisitRejectSerializer})
    def reject(self, reject_comment):
        self.date_of_tpm_rejected = timezone.now()
        self.reject_comment = reject_comment

        for recipient in self.unicef_focal_points_with_emails:
            self._send_email(
                recipient.email, 'tpm/visit/reject',
                cc=self._get_tpm_focal_points_as_email_recipients(),
                context={'recipient': recipient.get_full_name()}
            )

    @transition(status, source=[STATUSES.assigned], target=STATUSES.tpm_accepted,
                permission=_has_action_permission(action='accept'))
    def accept(self):
        self.date_of_tpm_accepted = timezone.now()

        for recipient in self.unicef_focal_points_with_emails:
            self._send_email(
                recipient.email, 'tpm/visit/accept',
                cc=self._get_tpm_focal_points_as_email_recipients(),
                context={'recipient': recipient.get_full_name()}
            )

    @transition(
        status, source=[STATUSES.tpm_accepted, STATUSES.tpm_report_rejected], target=STATUSES.tpm_reported,
        conditions=[
            TPMVisitReportValidations.as_condition(),
        ],
        permission=_has_action_permission(action='send_report'),
        custom={
            'name': _('Submit Report')
        }
    )
    def send_report(self):
        self.date_of_tpm_reported = timezone.now()

        for recipient in self.unicef_focal_points_with_emails:
            self._send_email(
                recipient.email, 'tpm/visit/report',
                cc=self._get_tpm_focal_points_as_email_recipients(),
                context={'recipient': recipient.get_full_name()}
            )

    @transition(
        status, source=[STATUSES.tpm_reported], target=STATUSES.tpm_report_rejected,
        permission=_has_action_permission(action='reject_report'),
        custom={
            'serializer': TPMVisitRejectSerializer,
            'name': _('Send back to TPM')
        }
    )
    def reject_report(self, reject_comment):
        self.date_of_tpm_report_rejected = timezone.now()
        TPMVisitReportRejectComment.objects.create(reject_reason=reject_comment, tpm_visit=self)

        for staff_user in self.tpm_partner_focal_points.filter(user__email__isnull=False, user__is_active=True):
            self._send_email(
                [staff_user.user.email], 'tpm/visit/report_rejected',
                context={'recipient': staff_user.user.get_full_name()}
            )

    @transition(status, source=[STATUSES.tpm_reported], target=STATUSES.unicef_approved,
                custom={'serializer': TPMVisitApproveSerializer},
                permission=_has_action_permission(action='approve'))
    def approve(self, mark_as_programmatic_visit=None, approval_comment=None, notify_focal_point=True,
                notify_tpm_partner=True):
        mark_as_programmatic_visit = mark_as_programmatic_visit or []

        self.tpm_activities.filter(id__in=mark_as_programmatic_visit).update(is_pv=True)

        self.date_of_unicef_approved = timezone.now()
        if notify_focal_point:
            for recipient in self.unicef_focal_points_with_emails:
                self._send_email(
                    recipient.email, 'tpm/visit/approve_report',
                    context={'recipient': recipient.get_full_name()}
                )

        if notify_tpm_partner:
            # TODO: Generate report as PDF attachment.
            for staff_user in self.tpm_partner_focal_points.filter(user__email__isnull=False, user__is_active=True):
                self._send_email(
                    [staff_user.user.email, ], 'tpm/visit/approve_report_tpm',
                    context={'recipient': staff_user.user.get_full_name()}
                )

        if approval_comment:
            self.approval_comment = approval_comment

    def get_object_url(self):
        return build_frontend_url('tpm', 'visits', self.id, 'details')


@python_2_unicode_compatible
class TPMVisitReportRejectComment(models.Model):
    rejected_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Rejected At'))

    # UNICEF rejected report
    reject_reason = models.TextField(verbose_name=_('Reason for Rejection'))

    tpm_visit = models.ForeignKey(
        TPMVisit, verbose_name=_('Visit'), related_name='report_reject_comments',
        on_delete=models.CASCADE,
    )

    def __str__(self):
        return 'Reject Comment #{0} for {1}'.format(self.id, self.tpm_visit)

    class Meta:
        verbose_name_plural = _('Report Reject Comments')
        ordering = ['tpm_visit', 'id']


@python_2_unicode_compatible
class TPMActivity(Activity):
    tpm_visit = models.ForeignKey(
        TPMVisit, verbose_name=_('Visit'), related_name='tpm_activities',
        on_delete=models.CASCADE,
    )

    unicef_focal_points = models.ManyToManyField(settings.AUTH_USER_MODEL, verbose_name=_('UNICEF Focal Points'),
                                                 related_name='+', blank=True)

    offices = models.ManyToManyField('users.Office', related_name='+', blank=True,
                                     verbose_name=_('Office(s) of UNICEF Focal Point(s)'))

    section = models.ForeignKey(
        'reports.Sector', related_name='tpm_activities', verbose_name=_('Section'),
        on_delete=models.CASCADE,
    )

    additional_information = models.TextField(verbose_name=_('Additional Information'), blank=True)

    attachments = CodedGenericRelation(Attachment, verbose_name=_('Activity Attachments'),
                                       code='activity_attachments', blank=True)
    report_attachments = CodedGenericRelation(Attachment, verbose_name=_('Activity Report'),
                                              code='activity_report', blank=True)

    is_pv = models.BooleanField(default=False, verbose_name=_('HACT Programmatic Visit'))

    def __str__(self):
        return 'Task #{0} for {1}'.format(self.id, self.tpm_visit)

    class Meta:
        verbose_name_plural = _('TPM Activities')
        ordering = ['tpm_visit', 'id', ]

    @property
    def related_reports(self):
        return Attachment.objects.filter(
            models.Q(
                object_id=self.tpm_visit_id,
                content_type__app_label=TPMVisit._meta.app_label,
                content_type__model=TPMVisit._meta.model_name,
                file_type__name='overall_report'
            ) | models.Q(
                object_id=self.id,
                content_type__app_label=TPMActivity._meta.app_label,
                content_type__model=TPMActivity._meta.model_name,
                file_type__name='report'
            )
        )

    @property
    def pv_applicable(self):
        return self.related_reports.exists()

    def get_mail_context(self):
        return {
            'locations': ', '.join(map(force_text, self.locations.all())),
            'intervention': self.intervention.title if self.intervention else '-',
            'cp_output': force_text(self.cp_output) if self.cp_output else '-',
            'section': force_text(self.section) if self.section else '-',
        }


@python_2_unicode_compatible
class TPMActionPoint(TimeStampedModel, models.Model):
    STATUSES = Choices(
        ('open', _('Open')),
        ('progress', _('In-Progress')),
        ('completed', _('Completed')),
        ('cancelled', _('Cancelled')),
    )

    tpm_visit = models.ForeignKey(
        TPMVisit, related_name='action_points', verbose_name=_('Visit'),
        on_delete=models.CASCADE,
    )

    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='created_tpm_action_points',
        verbose_name=_('Assigned By'),
        on_delete=models.CASCADE,
    )
    person_responsible = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='tpm_action_points',
        verbose_name=_('Person Responsible'),
        on_delete=models.CASCADE,
    )

    due_date = models.DateField(verbose_name=_('Due Date'))
    description = models.TextField(verbose_name=_('Description'))
    comments = models.TextField(blank=True, verbose_name=_('Comments'))

    status = models.CharField(choices=STATUSES, max_length=9, verbose_name='Status', default=STATUSES.open)

    def __str__(self):
        return 'Action Point #{} on {}'.format(self.id, self.tpm_activity)

    def get_mail_context(self):
        return {
            'person_responsible': self.person_responsible.get_full_name(),
            'author': self.author.get_full_name(),

        }

    def notify_person_responsible(self, template_name):
        context = {
            'environment': get_environment(),
            'visit': self.tpm_visit.get_mail_context(),
            'action_point': self.get_mail_context(),
        }

        send_notification_using_email_template(
            recipients=[self.person_responsible.email],
            email_template_name=template_name,
            context=context,
        )


PME = GroupWrapper(code='pme',
                   name='PME')

ThirdPartyMonitor = GroupWrapper(code='third_party_monitor',
                                 name='Third Party Monitor')

UNICEFUser = GroupWrapper(code='unicef_user',
                          name='UNICEF User')


class TPMPermissionsQueryset(StatusBasePermissionQueryset):
    def filter(self, *args, **kwargs):
        instance = kwargs.get('instance', None)
        if 'user' in kwargs and instance:
            kwargs['user_type'] = self.model._get_user_type(kwargs.pop('user'), instance=instance)
            return self.filter(**kwargs)

        if 'user' in kwargs and 'instance__in' in kwargs:
            user_type = self.model._get_user_type(kwargs.pop('user'))
            if user_type == UNICEFUser:
                return self.filter(models.Q(user_type=UNICEFUser.code) | models.Q(
                    user_type=self.model.USER_TYPES.unicef_focal_point)).filter(**kwargs)

            kwargs['user_type'] = user_type
            return self.filter(**kwargs)

        return super(TPMPermissionsQueryset, self).filter(**kwargs)


@python_2_unicode_compatible
class TPMPermission(StatusBasePermission):
    STATUSES = StatusBasePermission.STATUSES + TPMVisit.STATUSES

    USER_TYPES = Choices(
        ('unicef_focal_point', _('UNICEF Focal Point')),
        PME.as_choice(),
        ThirdPartyMonitor.as_choice(),
        UNICEFUser.as_choice(),
    )

    objects = TPMPermissionsQueryset.as_manager()

    def __str__(self):
        return '{} can {} {} in {} visit'.format(self.user_type, self.permission, self.target, self.instance_status)

    @classmethod
    def _get_user_type(cls, user, instance=None):
        if instance and TPMActivity.objects.filter(tpm_visit=instance, unicef_focal_points=user).exists():
            return cls.USER_TYPES.unicef_focal_point

        user_type = super(TPMPermission, cls)._get_user_type(user)
        if user_type == ThirdPartyMonitor:
            if not instance:
                return user_type

            try:
                member = user.tpmpartners_tpmpartnerstaffmember
            except TPMPartnerStaffMember.DoesNotExist:
                return None
            else:
                if member not in instance.tpm_partner.staff_members.all():
                    return None

        return user_type
