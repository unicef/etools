from django.contrib.contenttypes.fields import GenericRelation
from django.contrib.postgres.fields import ArrayField
from django.core.exceptions import ValidationError
from django.db import models, connection
from django.utils.translation import ugettext_lazy as _

from model_utils.models import TimeStampedModel

from unicef_locations.models import Location

from etools.applications.field_monitoring.settings.models import LocationSite, CPOutputConfig


class YearPlan(TimeStampedModel):
    ATTACHMENTS_FILE_TYPE_CODE = 'fm_year_plan'

    year = models.PositiveSmallIntegerField(primary_key=True)

    prioritization_criteria = models.TextField(verbose_name=_('Prioritization Criteria'), blank=True)
    methodology_notes = models.TextField(verbose_name=_('Methodology Notes & Standards'), blank=True)
    target_visits = models.PositiveSmallIntegerField(verbose_name=_('Target Visits For The Year'),
                                                     blank=True, default=0)
    modalities = models.TextField(verbose_name=_('Modalities'), blank=True)
    partner_engagement = models.TextField(verbose_name=_('Partner Engagement'), blank=True)
    other_aspects = GenericRelation('django_comments.Comment', object_id_field='object_pk',
                                    verbose_name=_('Other Aspects of the Field Monitoring Plan'), blank=True)
    attachments = GenericRelation('attachments.Attachment', verbose_name=_('Attachments'), blank=True)
    history = GenericRelation('unicef_snapshot.Activity', object_id_field='target_object_id',
                              content_type_field='target_content_type')

    def __str__(self):
        return 'Year Plan for {}'.format(self.year)


class Task(TimeStampedModel):
    year_plan = models.ForeignKey(YearPlan, verbose_name=_('Year Plan'), related_name='tasks')
    plan_by_month = ArrayField(models.PositiveSmallIntegerField(default=0, blank=True), default=[0]*12,
                               verbose_name=_('Plan By Month'), blank=True)
    location = models.ForeignKey(Location, verbose_name=_('Location'), related_name='tasks')
    location_site = models.ForeignKey(LocationSite, blank=True, null=True, verbose_name=_('Site'), related_name='tasks')
    cp_output_config = models.ForeignKey(CPOutputConfig, verbose_name=_('CP Output Config'), related_name='tasks')
    partner = models.ForeignKey('partners.PartnerOrganization', verbose_name=_('Partner'), related_name='tasks')
    intervention = models.ForeignKey('partners.Intervention', verbose_name=_('PD or SSFA'), related_name='+',
                                     blank=True, null=True)

    @property
    def reference_number(self):
        return '{}/{}/{}/FMT'.format(
            connection.tenant.country_short_code or '',
            self.created.year,
            self.id,
        )

    @staticmethod
    def clean_plan_by_month(plan):
        if not plan or len(plan) != 12 or any([month_plan < 0 for month_plan in plan]):
            raise ValidationError('Incorrect value in Plan By Month')

    def clean(self):
        type(self).clean_plan_by_month(self.plan_by_month)
