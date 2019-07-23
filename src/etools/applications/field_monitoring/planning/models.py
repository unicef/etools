from django.conf import settings
from django.contrib.contenttypes.fields import GenericRelation
from django.db import models, connection
from django.utils.translation import ugettext_lazy as _
from django_fsm import transition, FSMField
from model_utils import Choices

from model_utils.models import TimeStampedModel
from unicef_locations.models import Location

from etools.applications.core.permissions import import_permissions
from etools.applications.field_monitoring.fm_settings.models import Question, LocationSite
from etools.applications.partners.models import Intervention, PartnerOrganization
from etools.applications.reports.models import Result
from etools.applications.tpm.tpmpartners.models import TPMPartner
from etools.libraries.djangolib.models import SoftDeleteMixin


class YearPlan(TimeStampedModel):
    year = models.PositiveSmallIntegerField(primary_key=True)

    prioritization_criteria = models.TextField(verbose_name=_('Prioritization Criteria'), blank=True)
    methodology_notes = models.TextField(verbose_name=_('Methodology Notes & Standards'), blank=True)
    target_visits = models.PositiveSmallIntegerField(verbose_name=_('Target Visits For The Year'),
                                                     blank=True, default=0)
    modalities = models.TextField(verbose_name=_('Modalities'), blank=True)
    partner_engagement = models.TextField(verbose_name=_('Partner Engagement'), blank=True)
    other_aspects = models.TextField(verbose_name=_('Other Aspects of the Field Monitoring Plan'), blank=True)
    history = GenericRelation('unicef_snapshot.Activity', object_id_field='target_object_id',
                              content_type_field='target_content_type')

    class Meta:
        verbose_name = _('Year Plan')
        verbose_name_plural = _('Year Plans')
        ordering = ('year',)

    @classmethod
    def get_defaults(cls, year):
        previous_year_plan = cls._default_manager.filter(year=int(year) - 1).first()
        if not previous_year_plan:
            return {}

        return {
            field: getattr(previous_year_plan, field) for field in
            ['prioritization_criteria', 'methodology_notes', 'target_visits', 'modalities', 'partner_engagement']
            if getattr(previous_year_plan, field)
        }

    def __str__(self):
        return 'Year Plan for {}'.format(self.year)


class QuestionTargetMixin(models.Model):
    partner = models.ForeignKey(PartnerOrganization, blank=True, null=True, verbose_name=_('Partner'),
                                on_delete=models.CASCADE)
    cp_output = models.ForeignKey(Result, blank=True, null=True, verbose_name=_('Partner'),
                                  on_delete=models.CASCADE)
    intervention = models.ForeignKey(Intervention, blank=True, null=True, verbose_name=_('Partner'),
                                     on_delete=models.CASCADE)

    @property
    def related_to(self):
        return self.partner or self.cp_output or self.intervention

    class Meta:
        abstract = True


class QuestionTemplate(QuestionTargetMixin, models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, verbose_name=_('Question'))
    is_active = models.BooleanField(default=True, verbose_name=_('Is Active'))
    specific_details = models.TextField(verbose_name=_('Specific Details To Probe'), blank=True)

    class Meta:
        verbose_name = _('Question Template')
        verbose_name_plural = _('Question Templates')
        ordering = ('id',)

    def __str__(self):
        return 'Question Template for {}'.format(self.related_to)


class MonitoringActivity(SoftDeleteMixin, TimeStampedModel):
    TYPES = Choices(
        ('staff', _('Staff')),
        ('tpm', _('TPM')),
    )

    STATUSES = Choices(
        ('draft', _('Draft')),
        ('details_configured', _('Details Configured')),
        ('checklist_configured', _('Checklist Configured')),
        ('assigned', _('Assigned')),
        ('accepted', _('Accepted')),
        ('data_collected', _('Data Collected')),
        ('report_submitted', _('Report Submitted')),
        ('completed', _('Completed')),
        ('cancelled', _('Cancelled')),
    )

    TRANSITION_SIDE_EFFECTS = {
    }

    AUTO_TRANSITIONS = {
        'assigned': ['accepted']
    }

    activity_type = models.CharField(max_length=10, choices=TYPES)

    tpm_partner = models.ForeignKey(TPMPartner, blank=True, null=True, verbose_name=_('TPM Partner'),
                                    on_delete=models.CASCADE)
    team_members = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True, verbose_name=_('Team Members'),
                                          related_name='monitoring_activities')
    person_responsible = models.ForeignKey(settings.AUTH_USER_MODEL, blank=True, null=True,
                                           verbose_name=_('Person Responsible'), related_name='+',
                                           on_delete=models.SET_NULL)

    location = models.ForeignKey(Location, verbose_name=_('Location'), related_name='monitoring_activities',
                                 on_delete=models.CASCADE)
    location_site = models.ForeignKey(LocationSite, blank=True, null=True, verbose_name=_('Site'),
                                      related_name='monitoring_activities', on_delete=models.CASCADE)

    partners = models.ManyToManyField(PartnerOrganization, verbose_name=_('Partner'), related_name='+', blank=True)
    interventions = models.ManyToManyField(Intervention, verbose_name=_('PD/SSFA'), related_name='+', blank=True)
    cp_outputs = models.ManyToManyField(Result, verbose_name=_('Outputs'), related_name='+', blank=True)

    start_date = models.DateField(verbose_name=_('Start Date'), blank=True, null=True)
    end_date = models.DateField(verbose_name=_('End Date'), blank=True, null=True)

    status = FSMField(verbose_name=_('Status'), max_length=20, choices=STATUSES, default=STATUSES.draft)

    class Meta:
        verbose_name = _('Monitoring Activity')
        verbose_name_plural = _('Monitoring Activities')
        ordering = ('id',)

    def __str__(self):
        return self.reference_number

    @property
    def reference_number(self):
        return '{}/{}/{}/FMA'.format(
            connection.tenant.country_short_code or '',
            self.created.year,
            self.id,
        )

    @classmethod
    def permission_structure(cls):
        permissions = import_permissions(cls.__name__)
        return permissions

    @transition(field=status, source=STATUSES.draft, target=STATUSES.details_configured)
    def mark_details_configured(self):
        pass

    @transition(field=status, source=STATUSES.details_configured, target=STATUSES.checklist_configured)
    def mark_checklist_configured(self):
        pass

    @transition(field=status, source=STATUSES.checklist_configured, target=[STATUSES.assigned])
    def assign(self):
        pass

    @transition(field=status, source=STATUSES.assigned, target=[STATUSES.accepted])
    def accept(self):
        pass

    @transition(field=status, source=STATUSES.assigned, target=STATUSES.draft)
    def reject(self):
        pass

    @transition(field=status, source=STATUSES.accepted, target=STATUSES.data_collected)
    def mark_data_collected(self):
        pass

    @transition(field=status, source=STATUSES.data_collected, target=STATUSES.report_submitted)
    def submit_report(self):
        pass

    @transition(field=status, source=STATUSES.report_submitted, target=STATUSES.completed)
    def complete(self):
        pass

    @transition(field=status, target=STATUSES.cancelled,
                source=[
                    STATUSES.draft, STATUSES.details_configured, STATUSES.checklist_configured,
                    STATUSES.assigned, STATUSES.accepted, STATUSES.data_collected
                ])
    def cancel(self):
        pass
