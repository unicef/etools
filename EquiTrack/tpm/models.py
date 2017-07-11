from __future__ import unicode_literals

from django.conf import settings
from django.contrib.contenttypes.fields import GenericRelation
from django.contrib.postgres.fields import ArrayField
from django.core.exceptions import ValidationError
from django.db import models
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
from utils.common.urlresolvers import site_url
from utils.groups.wrappers import GroupWrapper
from utils.permissions import has_action_permission
from utils.permissions.models.models import StatusBasePermission
from utils.permissions.models.query import StatusBasePermissionQueryset
from .transitions.serializers import TPMVisitRejectSerializer
from .transitions.conditions import ValidateTPMVisitActivities, \
                                    TPMVisitReportValidations, TPMVisitSubmitRequiredFieldsCheck


class TPMPartner(BaseFirm):
    STATUSES = Choices(
        ('draft', _('Draft')),
        ('active', _('Active')),
        ('cancelled', _('Cancelled')),
    )

    status = FSMField(_('status'), max_length=20, choices=STATUSES, default=STATUSES.draft, protected=True)
    attachments = GenericRelation(Attachment, verbose_name=_('attachments'), blank=True)

    # TODO: Remove hardcode for PME permissions?
    @transition(status, source=[STATUSES.draft, STATUSES.cancelled], target=STATUSES.active,
                permission=lambda instance, user: PME.as_group() in user.groups.all())
    def activate(self):
        pass

    @transition(status, source=[STATUSES.draft, STATUSES.active], target=STATUSES.cancelled,
                permission=lambda instance, user: PME.as_group() in user.groups.all())
    def cancel(self):
        pass


class TPMPartnerStaffMember(BaseStaffMember):
    tpm_partner = models.ForeignKey(TPMPartner, verbose_name=_('TPM Vendor'), related_name='staff_members')

    receive_tpm_notifications = models.BooleanField(verbose_name=_('Receive Notifications on TPM Tasks'), default=False)


def _has_action_permission(action):
    return lambda instance=None, user=None: has_action_permission(TPMPermission, instance=instance, user=user, action=action)


@python_2_unicode_compatible
class TPMVisit(SoftDeleteMixin, TimeStampedModel, models.Model):
    STATUSES = Choices(
        ('draft', _('Draft')),
        ('assigned', _('Assigned')),
        ('tpm_accepted', _('TPM Accepted')),
        ('tpm_rejected', _('TPM Rejected')),
        ('tpm_reported', _('TPM Reported')),
        ('submitted', _('Submitted')),
        ('unicef_approved', _('Approved')),
    )

    tpm_partner = models.ForeignKey(TPMPartner, verbose_name=_('TPM Vendor'))

    status = FSMField(verbose_name=_('status'), max_length=20, choices=STATUSES, default=STATUSES.draft, protected=True)

    reject_comment = models.TextField(verbose_name=_('Request for more information'), blank=True)

    attachments = CodedGenericRelation(Attachment, verbose_name=_('Related Documents'), code='attach', blank=True)
    report = CodedGenericRelation(Attachment, verbose_name=_('Report'), code='report', blank=True)

    @property
    def reference_number(self):
        start_year = self.visit_start.year
        end_year = self.visit_end.year
        return '{0}/{1}/{2}'.format(
            self.created.year,
            self.tpm_partner.vendor_number,
            self.id
        )

    @property
    def start_date(self):
        # TODO: Rewrite to reduce number of SQL queries.
        return TPMLocation.objects.filter(tpm_low_result__tpm_sector__tpm_activity__tpm_visit=self).aggregate(
            models.Min('start_date'))['start_date__min']

    @property
    def end_date(self):
        # TODO: Rewrite to reduce number of SQL queries.
        return TPMLocation.objects.filter(tpm_low_result__tpm_sector__tpm_activity__tpm_visit=self).aggregate(
            models.Max('end_date'))['end_date__max']

    def __str__(self):
        return 'Visit ({}, {})'.format(self.tpm_partner, ', '.join(self.tpm_activities.values_list('partnership__title', flat=True)))

    def has_action_permission(self, user=None, action=None):
        return _has_action_permission(self, user, action)

    def _send_email(self, recipients, template_name, context=None, **kwargs):
        context = context or {}

        base_context = {
            'visit': self,
            'url': site_url(),
            'environment': get_environment(),
        }
        base_context.update(context)
        context = base_context

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

    def _get_tpm_as_email_recipients(self):
        return list(self.tpm_partner.staff_members.filter(receive_tpm_notifications=True, user__email__isnull=False).values_list('user__email',
                                                                                                 flat=True))

    def _get_unicef_focal_points_as_email_recipients(self):
        return list(self.tpm_activities.filter(unicef_focal_points__email__isnull=False).values_list('unicef_focal_points__email', flat=True))

    def _get_ip_focal_points_as_email_recipients(self):
        return list(self.tpm_activities.filter(partnership__partner_focal_points__email__isnull=False).values_list('partnership__partner_focal_points__email', flat=True))

    @transition(status, source=[STATUSES.draft], target=STATUSES.assigned,
                conditions=[ValidateTPMVisitActivities.as_condition()],
                permission=_has_action_permission(action='assign'))
    def assign(self):
        self._send_email(self._get_tpm_as_email_recipients(), 'tpm/visit/assign',
                         cc=self._get_unicef_focal_points_as_email_recipients())

    @transition(status, source=[STATUSES.assigned], target=STATUSES.tpm_rejected,
                permission=_has_action_permission(action='reject'),
                custom={'serializer': TPMVisitRejectSerializer})
    def reject(self, reject_comment):
        self.reject_comment = reject_comment

        self._send_email(self._get_unicef_focal_points_as_email_recipients(), 'tpm/visit/reject',
                         cc=self._get_tpm_as_email_recipients())

    @transition(status, source=[STATUSES.assigned], target=STATUSES.tpm_accepted,
                permission=_has_action_permission(action='accept'))
    def accept(self):
        self._send_email(self._get_unicef_focal_points_as_email_recipients(), 'tpm/visit/accept',
                         cc=self._get_tpm_as_email_recipients())

    @transition(status, source=[STATUSES.tpm_accepted], target=STATUSES.tpm_reported,
                conditions=[
                    TPMVisitReportValidations.as_condition(),
                ],
                permission=_has_action_permission(action='send_report'))
    def send_report(self):
        self._send_email(self._get_unicef_focal_points_as_email_recipients(), 'tpm/visit/report',
                         cc=self._get_tpm_as_email_recipients())

    # TODO: Do we need this transition?
    # @transition(status, source=[STATUSES.draft, STATUSES.tpm_rejected], target=STATUSES.submitted,
    #             permission=_has_action_permission(action='submit'))
    # def submit(self):
    #     pass

    @transition(status, source=[STATUSES.tpm_reported], target=STATUSES.unicef_approved,
                permission=_has_action_permission(action='approve'))
    def approve(self, mark_as_programmatic_visit=True, notify_focal_point=True, notify_partner=True):
        if notify_focal_point:
            self._send_email(self._get_unicef_focal_points_as_email_recipients(), 'tpm/visit/approve')

        if notify_partner:
            # TODO: Generate report as PDF attachment.
            self._send_email(self._get_ip_focal_points_as_email_recipients(), 'tpm/visit/report_for_ip')

    def get_object_url(self):
        return ''


@python_2_unicode_compatible
class TPMActivity(models.Model):
    partnership = models.ForeignKey('partners.Intervention', verbose_name=_('partnership'))

    tpm_visit = models.ForeignKey(TPMVisit, verbose_name=_('visit'), related_name='tpm_activities')

    unicef_focal_points = models.ManyToManyField(settings.AUTH_USER_MODEL, verbose_name=_('UNICEF Focal Point'), related_name='tpm_activities')

    def __str__(self):
        return 'Activity #{0} for {1}'.format(self.id, self.tpm_visit)

    class Meta:
        verbose_name_plural = _('TPM Activities')


@python_2_unicode_compatible
class TPMSectorCovered(models.Model):
    sector = models.ForeignKey('reports.Sector', verbose_name=_('Sector covered'), blank=True)
    tpm_activity = models.ForeignKey(TPMActivity, verbose_name=_('activity'), related_name='tpm_sectors')

    def __str__(self):
        return 'Sector {0} for {1}'.format(self.sector, self.tpm_activity)

    class Meta:
        verbose_name_plural = _('TPM Sectors Covered')


@python_2_unicode_compatible
class TPMLowResult(models.Model):
    # TODO: Results is LowerResult? (TPM Spec: Low-level Results  (see PD/SSFA Output [array]0..* in Partnership Management))
    result = models.ForeignKey('partners.InterventionResultLink', verbose_name=_('PD/SSFA Output'))
    tpm_sector = models.ForeignKey(TPMSectorCovered, verbose_name=_('sector'), related_name='tpm_low_results')

    def __str__(self):
        return 'Result {0} for {1}'.format(self.result, self.tpm_sector)


@python_2_unicode_compatible
class TPMLocation(models.Model):
    tpm_low_result = models.ForeignKey(TPMLowResult, verbose_name=_('low_result'), null=True, blank=True, related_name='tpm_locations')

    start_date = models.DateField(verbose_name=_('Start Date'), null=True, blank=True)
    end_date = models.DateField(verbose_name=_('End Date'), null=True, blank=True)

    location = models.ForeignKey('locations.Location', verbose_name=_('Location'))
    type_of_site = models.CharField(verbose_name=_('Type of site'), max_length=255, blank=True)

    def __str__(self):
        return '{}: {}'.format(self.tpm_low_result, self.location)


UNICEFFocalPoint = GroupWrapper(code='unicef_focal_point',
                                name='UNICEF Focal Point')

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
                return self.filter(models.Q(user_type=UNICEFUser.code) | models.Q(user_type=UNICEFFocalPoint.code)) \
                    .filter(**kwargs)

            kwargs['user_type'] = user_type
            return self.filter(**kwargs)

        return super(TPMPermissionsQueryset, self).filter(**kwargs)


@python_2_unicode_compatible
class TPMPermission(StatusBasePermission):
    STATUSES = StatusBasePermission.STATUSES + TPMVisit.STATUSES

    USER_TYPES = Choices(
        UNICEFFocalPoint.as_choice(),
        PME.as_choice(),
        ThirdPartyMonitor.as_choice(),
        UNICEFUser.as_choice(),
    )

    objects = TPMPermissionsQueryset.as_manager()

    def __str__(self):
        return '{} can {} {} in {} visit'.format(self.user_type, self.permission, self.target, self.instance_status)

    @classmethod
    def _get_user_type(cls, user, instance=None):
        if instance and instance.tpm_activities.filter(unicef_focal_points=user).exists():
            return UNICEFFocalPoint.code

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
