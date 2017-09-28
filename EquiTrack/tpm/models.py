from __future__ import unicode_literals

from django.conf import settings
from django.contrib.contenttypes.fields import GenericRelation
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone, six
from django.utils.encoding import python_2_unicode_compatible
from django_fsm import FSMField, transition
from django.utils.translation import ugettext_lazy as _
from model_utils import Choices
from model_utils.models import TimeStampedModel
from post_office import mail

from EquiTrack.utils import get_environment
from attachments.models import Attachment
from firms.models import BaseFirm, BaseStaffMember
from publics.models import SoftDeleteMixin
from utils.common.models.fields import CodedGenericRelation
from utils.common.urlresolvers import site_url, build_frontend_url
from utils.groups.wrappers import GroupWrapper
from utils.permissions.utils import has_action_permission
from utils.permissions.models.models import StatusBasePermission
from utils.permissions.models.query import StatusBasePermissionQueryset
from .transitions.serializers import TPMVisitRejectSerializer, TPMVisitApproveSerializer
from .transitions.conditions import ValidateTPMVisitActivities, \
                                    TPMVisitReportValidations, TPMVisitAssignRequiredFieldsCheck


@python_2_unicode_compatible
class TPMPartner(BaseFirm):
    STATUSES = Choices(
        ('draft', _('Draft')),
        ('active', _('Active')),
        ('cancelled', _('Cancelled')),
    )

    STATUSES_DATES = {
        STATUSES.draft: 'date_created',
        STATUSES.active: 'date_of_active',
        STATUSES.cancelled: 'date_of_cancel',
    }

    status = FSMField(_('status'), max_length=20, choices=STATUSES, default=STATUSES.draft, protected=True)
    attachments = GenericRelation(Attachment, verbose_name=_('attachments'), blank=True)

    date_of_active = models.DateField(blank=True, null=True)
    date_of_cancel = models.DateField(blank=True, null=True)

    def __str__(self):
        return self.name

    @property
    def date_created(self):
        return self.created.date()

    @property
    def status_date(self):
        return getattr(self, self.STATUSES_DATES[self.status])

    # TODO: Remove hardcode for PME permissions?
    @transition(status, source=[STATUSES.draft, STATUSES.cancelled], target=STATUSES.active,
                permission=lambda instance, user: PME.as_group() in user.groups.all())
    def activate(self):
        self.date_of_active = timezone.now()

    @transition(status, source=[STATUSES.draft, STATUSES.active], target=STATUSES.cancelled,
                permission=lambda instance, user: PME.as_group() in user.groups.all())
    def cancel(self):
        self.date_of_cancel = timezone.now()


@python_2_unicode_compatible
class TPMPartnerStaffMember(BaseStaffMember):
    tpm_partner = models.ForeignKey(TPMPartner, verbose_name=_('TPM Vendor'), related_name='staff_members')

    receive_tpm_notifications = models.BooleanField(verbose_name=_('Receive Notifications on TPM Tasks'), default=False)

    def __str__(self):
        return self.get_full_name()


def _has_action_permission(action):
    return lambda instance=None, user=None: \
        has_action_permission(TPMPermission, instance=instance, user=user, action=action)


@python_2_unicode_compatible
class TPMVisit(SoftDeleteMixin, TimeStampedModel, models.Model):
    STATUSES = Choices(
        ('draft', _('Draft')),
        ('assigned', _('Assigned')),
        ('cancelled', _('Cancelled')),
        ('tpm_accepted', _('TPM Accepted')),
        ('tpm_rejected', _('TPM Rejected')),
        ('tpm_reported', _('TPM Reported')),
        ('tpm_report_rejected', _('Sent Back to TPM')),
        ('unicef_approved', _('UNICEF Approved')),
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

    tpm_partner = models.ForeignKey(TPMPartner, verbose_name=_('TPM Vendor'), null=True)

    status = FSMField(verbose_name=_('status'), max_length=20, choices=STATUSES, default=STATUSES.draft, protected=True)

    reject_comment = models.TextField(verbose_name=_('Request for more information'), blank=True)
    approval_comment = models.TextField(verbose_name=_('Approval comments'), blank=True)

    report_attachments = CodedGenericRelation(Attachment, verbose_name=_('Visit Report'),
                                              code='visit_report', blank=True)

    visit_information = models.TextField(verbose_name=_('Visit Information'), blank=True)

    date_of_assigned = models.DateField(blank=True, null=True)
    date_of_cancelled = models.DateField(blank=True, null=True)
    date_of_tpm_accepted = models.DateField(blank=True, null=True)
    date_of_tpm_rejected = models.DateField(blank=True, null=True)
    date_of_tpm_reported = models.DateField(blank=True, null=True)
    date_of_tpm_report_rejected = models.DateField(blank=True, null=True)
    date_of_unicef_approved = models.DateField(blank=True, null=True)

    offices = models.ManyToManyField('users.Office', related_name='tpm_visits', blank=True,
                                     verbose_name=_('Office(s) of UNICEF Focal Point(s)'))

    unicef_focal_points = models.ManyToManyField(settings.AUTH_USER_MODEL, verbose_name=_('UNICEF Focal Points'),
                                                 related_name='tpm_visits', blank=True)

    tpm_partner_focal_points = models.ManyToManyField(
        TPMPartnerStaffMember, verbose_name=_('TPM Focal Points'), related_name='tpm_visits', blank=True
    )

    @property
    def date_created(self):
        return self.created.date()

    @property
    def status_date(self):
        return getattr(self, self.STATUSES_DATES[self.status])

    @property
    def reference_number(self):
        return '{0}/{1}/{2}'.format(
            self.created.year,
            self.tpm_partner.vendor_number if self.tpm_partner else '--',
            self.id
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

    def __str__(self):
        return 'Visit ({}, {})'.format(
            self.tpm_partner, ', '.join(self.tpm_activities.values_list('partnership__title', flat=True))
        )

    def has_action_permission(self, user=None, action=None):
        return _has_action_permission(self, user, action)

    def _send_email(self, recipients, template_name, context=None, **kwargs):
        context = context or {}

        base_context = {
            'visit': self,
            'url': site_url(),
            'environment': get_environment(),
            'implementing_partners': set(map(lambda a: a.implementing_partner.name, self.tpm_activities.all())),
            'partnerships': set(map(lambda a: a.partnership.title, self.tpm_activities.all())),
        }
        base_context.update(context)
        context = base_context

        if isinstance(recipients, six.string_types):
            recipients = [recipients, ]
        else:
            recipients = list(recipients)

        # assert recipients
        if recipients:
            mail.send(
                recipients,
                settings.DEFAULT_FROM_EMAIL,
                template=template_name,
                context=context,
                **kwargs
            )

    def _get_unicef_focal_points_as_email_recipients(self):
        return list(
            self.unicef_focal_points.filter(
                email__isnull=False
            ).values_list('email', flat=True)
        )

    def _get_tpm_focal_points_as_email_recipients(self):
        return list(
            self.tpm_partner_focal_points.filter(
                user__email__isnull=False
            ).values_list('user__email', flat=True)
        )

    def _get_ip_focal_points_as_email_recipients(self):
        return list(
            self.tpm_activities.filter(
                partnership__partner_focal_points__email__isnull=False
            ).values_list('partnership__partner_focal_points__email', flat=True)
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

    @transition(
        status, source=[
            STATUSES.draft, STATUSES.assigned, STATUSES.tpm_accepted, STATUSES.tpm_rejected,
            STATUSES.tpm_reported, STATUSES.tpm_report_rejected,
        ], target=STATUSES.cancelled, permission=_has_action_permission(action='cancel'),
        custom={
            'name': _('Cancel Visit')
        }
    )
    def cancel(self):
        self.date_of_cancelled = timezone.now()

    @transition(status, source=[STATUSES.assigned], target=STATUSES.tpm_rejected,
                permission=_has_action_permission(action='reject'),
                custom={'serializer': TPMVisitRejectSerializer})
    def reject(self, reject_comment):
        self.date_of_tpm_rejected = timezone.now()
        self.reject_comment = reject_comment

        for recipient in self.unicef_focal_points.filter(email__isnull=False):
            self._send_email(
                recipient.email, 'tpm/visit/reject',
                cc=self._get_tpm_focal_points_as_email_recipients(),
                context={'recipient': recipient}
            )

    @transition(status, source=[STATUSES.assigned], target=STATUSES.tpm_accepted,
                permission=_has_action_permission(action='accept'))
    def accept(self):
        self.date_of_tpm_accepted = timezone.now()

        for recipient in self.unicef_focal_points.filter(email__isnull=False):
            self._send_email(
                recipient.email, 'tpm/visit/accept',
                cc=self._get_tpm_focal_points_as_email_recipients(),
                context={'recipient': recipient}
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

        for recipient in self.unicef_focal_points.filter(email__isnull=False):
            self._send_email(
                recipient.email, 'tpm/visit/report',
                cc=self._get_tpm_focal_points_as_email_recipients(),
                context={'recipient': recipient}
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

        for staff_user in self.tpm_partner_focal_points.filter(user__email__isnull=False):
            self._send_email(
                [staff_user.user.email], 'tpm/visit/report_rejected',
                context={'recipient': staff_user.user}
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
            for recipient in self.unicef_focal_points.filter(email__isnull=False):
                self._send_email(
                    recipient.email, 'tpm/visit/approve_report',
                    context={'recipient': recipient}
                )

        if notify_tpm_partner:
            # TODO: Generate report as PDF attachment.
            for staff_user in self.tpm_partner_focal_points.filter(user__email__isnull=False):
                self._send_email(
                    [staff_user.user.email, ], 'tpm/visit/approve_report_tpm',
                    context={'recipient': staff_user.user}
                )

        if approval_comment:
            self.approval_comment = approval_comment

    def get_object_url(self):
        return build_frontend_url('tpm', 'visits', self.id, 'details')


@python_2_unicode_compatible
class TPMVisitReportRejectComment(models.Model):
    rejected_at = models.DateTimeField(auto_now_add=True)

    reject_reason = models.TextField()

    tpm_visit = models.ForeignKey(TPMVisit, verbose_name=_('visit'), related_name='report_reject_comments')

    def __str__(self):
        return 'Reject Comment #{0} for {1}'.format(self.id, self.tpm_visit)

    class Meta:
        verbose_name_plural = _('Report Reject Comments')
        ordering = ['tpm_visit', 'id']


@python_2_unicode_compatible
class TPMActivity(models.Model):
    tpm_visit = models.ForeignKey(TPMVisit, verbose_name=_('visit'), related_name='tpm_activities')

    implementing_partner = models.ForeignKey('partners.PartnerOrganization', verbose_name=_('Implementing Partner'))
    partnership = models.ForeignKey('partners.Intervention', verbose_name=_('partnership'))
    cp_output = models.ForeignKey('reports.Result', verbose_name=_('CP Output'), null=True, blank=True)

    locations = models.ManyToManyField('locations.Location', verbose_name=_('Locations'), related_name='tpm_activities')
    section = models.ForeignKey('users.Section', related_name='tpm_activities')

    additional_information = models.TextField(verbose_name=_('Additional Information'), blank=True)

    attachments = CodedGenericRelation(Attachment, verbose_name=_('Activity Attachments'),
                                       code='activity_attachments', blank=True)
    report_attachments = CodedGenericRelation(Attachment, verbose_name=_('Activity Report'),
                                              code='activity_report', blank=True)

    is_pv = models.BooleanField(default=False, verbose_name=_('Programmatic Visit'))

    date = models.DateField(blank=True, null=True)

    def __str__(self):
        return 'Activity #{0} for {1}'.format(self.id, self.tpm_visit)

    class Meta:
        verbose_name_plural = _('TPM Activities')
        ordering = ['tpm_visit', 'id', ]


@python_2_unicode_compatible
class TPMActionPoint(TimeStampedModel, models.Model):
    STATUSES = Choices(
        ('open', 'Open'),
        ('progress', 'In-Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    )

    tpm_visit = models.ForeignKey(TPMVisit, related_name='action_points')

    author = models.ForeignKey(User, related_name='created_tpm_action_points')
    person_responsible = models.ForeignKey(User, related_name='tpm_action_points')

    due_date = models.DateField()
    description = models.TextField()
    comments = models.TextField(blank=True)

    status = models.CharField(choices=STATUSES, max_length=9, verbose_name='Status', default=STATUSES.open)

    def __str__(self):
        return 'Action Point #{} on {}'.format(self.id, self.tpm_activity)

    def notify_person_responsible(self, template_name):
        context = {
            'url': site_url(),
            'environment': get_environment(),
            'visit': self.tpm_visit,
            'action_point': self,
            'implementing_partners': set(map(
                lambda a: a.implementing_partner.name,
                self.tpm_visit.tpm_activities.all()
            )),
            'partnerships': set(map(
                lambda a: a.partnership.title,
                self.tpm_visit.tpm_activities.all()
            )),
        }

        mail.send(
            self.person_responsible.email,
            settings.DEFAULT_FROM_EMAIL,
            cc=[self.author.email],
            template=template_name,
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
        if 'user' in kwargs and 'instance' in kwargs and kwargs['instance']:
            kwargs['user_type'] = self.model._get_user_type(kwargs.pop('user'), instance=kwargs['instance'])
            return self.filter(**kwargs)

        if 'user' in kwargs and 'instance__in' in kwargs:
            user_type = self.model._get_user_type(kwargs.pop('user'))
            if user_type == UNICEFUser:
                return self.filter(models.Q(user_type=UNICEFUser.code)
                                   | models.Q(user_type=self.model.USER_TYPES.unicef_focal_point)).filter(**kwargs)

            kwargs['user_type'] = user_type
            return self.filter(**kwargs)

        return super(TPMPermissionsQueryset, self).filter(**kwargs)


@python_2_unicode_compatible
class TPMPermission(StatusBasePermission):
    STATUSES = StatusBasePermission.STATUSES + TPMVisit.STATUSES

    USER_TYPES = Choices(
        ('unicef_focal_point', 'UNICEF Focal Point'),
        PME.as_choice(),
        ThirdPartyMonitor.as_choice(),
        UNICEFUser.as_choice(),
    )

    objects = TPMPermissionsQueryset.as_manager()

    def __str__(self):
        return '{} can {} {} in {} visit'.format(self.user_type, self.permission, self.target, self.instance_status)

    @classmethod
    def _get_user_type(cls, user, instance=None):
        if instance and instance.unicef_focal_points.filter(id=user.id).exists():
            return cls.USER_TYPES.unicef_focal_point

        user_type = super(TPMPermission, cls)._get_user_type(user)
        if user_type == ThirdPartyMonitor:
            if not instance:
                return user_type

            try:
                if user.tpm_tpmpartnerstaffmember not in instance.tpm_partner.staff_members.all():
                    return None
            except TPMPartnerStaffMember.DoesNotExist:
                return None

        return user_type
