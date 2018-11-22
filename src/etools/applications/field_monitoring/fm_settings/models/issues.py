from django.conf import settings
from django.contrib.contenttypes.fields import GenericRelation
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import ugettext_lazy as _

from model_utils import Choices
from model_utils.models import TimeStampedModel

from unicef_locations.models import Location

from etools.applications.field_monitoring.fm_settings.models import LocationSite
from etools.applications.partners.models import PartnerOrganization
from etools.applications.reports.models import Result


class LogIssue(TimeStampedModel):
    STATUS_CHOICES = Choices(
        ('new', 'New'),
        ('past', 'Past'),
    )
    RELATED_TO_TYPE_CHOICES = Choices(
        ('cp_output', _('CP Output')),
        ('partner', _('CP Output')),
        ('location_site', _('Location/Site')),
    )

    author = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='created_logissues',
                               verbose_name=_('Issue Raised By'))
    cp_output = models.ForeignKey(Result, blank=True, null=True, verbose_name=_('CP Output'))
    partner = models.ForeignKey(PartnerOrganization, blank=True, null=True, verbose_name=_('Partner'))
    location = models.ForeignKey(Location, blank=True, null=True, verbose_name=_('Location'))
    location_site = models.ForeignKey(LocationSite, blank=True, null=True, verbose_name=_('Site'))

    issue = models.TextField(verbose_name=_('Issue For Attention/Probing'))
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_CHOICES.new)
    attachments = GenericRelation('attachments.Attachment', verbose_name=_('Attachments'), blank=True)
    history = GenericRelation('unicef_snapshot.Activity', object_id_field='target_object_id',
                              content_type_field='target_content_type')

    def __str__(self):
        return '{}: {}'.format(self.related_to, self.issue)

    @property
    def related_to(self):
        return self.cp_output or self.partner or self.location or self.location_site
