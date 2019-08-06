from django.db import models
from django.utils.translation import ugettext as _

from model_utils.models import TimeStampedModel

from etools.applications.reports.models import Section


class SectionHistory(TimeStampedModel):
    """ Model to keep history of Section changes"""
    CREATE = 'create'
    MERGE = 'merge'
    CLOSE = 'close'

    TYPES = (
        (CREATE, 'Create'),
        (MERGE, 'Merge'),
        (CLOSE, 'Close'),
    )

    from_sections = models.ManyToManyField(Section, blank=True, verbose_name=_('From'), related_name='history_from')
    to_sections = models.ManyToManyField(Section, blank=True, verbose_name=_('To'), related_name='history_to')

    history_type = models.CharField(verbose_name=_("Name"), max_length=10, choices=TYPES)
