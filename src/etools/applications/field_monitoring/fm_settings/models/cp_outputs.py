from django.db import models
from django.utils.translation import ugettext_lazy as _

from model_utils.models import TimeStampedModel

from etools.applications.field_monitoring.fm_settings.models import CheckListItem, FMMethodType
from etools.applications.field_monitoring.shared.models import FMMethod
from etools.applications.reports.models import ResultType, Sector


class CPOutputConfig(TimeStampedModel):
    cp_output = models.OneToOneField('reports.Result', related_name='fm_config',
                                     verbose_name=_('CP Output To Be Monitored'),
                                     on_delete=models.CASCADE)
    is_monitored = models.BooleanField(default=True, verbose_name=_('Monitored At Community Level?'))
    is_priority = models.BooleanField(verbose_name=_('Priority?'), default=False)
    government_partners = models.ManyToManyField('partners.PartnerOrganization', blank=True,
                                                 verbose_name=_('Contributing Government Partners'))
    recommended_method_types = models.ManyToManyField(FMMethodType, blank=True, verbose_name=_('Method(s)'))
    sections = models.ManyToManyField(Sector, blank=True, verbose_name=_('Sections'))

    class Meta:
        verbose_name = _('CP Output Config')
        verbose_name_plural = _('CP Output Configs')
        ordering = ('id',)

    def __str__(self):
        if self.cp_output.result_type.name == ResultType.OUTPUT:
            return self.cp_output.output_name
        return self.cp_output.result_name


class PlannedCheckListItem(models.Model):
    checklist_item = models.ForeignKey(CheckListItem, verbose_name=_('Checklist Item'),
                                       on_delete=models.CASCADE)
    cp_output_config = models.ForeignKey(CPOutputConfig, verbose_name=_('CP Output Config'),
                                         related_name='planned_checklist_items',
                                         on_delete=models.CASCADE)
    methods = models.ManyToManyField(FMMethod, blank=True, verbose_name=_('Method(s)'))

    class Meta:
        verbose_name = _('Planned Checklist Item')
        verbose_name_plural = _('Planned Checklist Items')
        ordering = ('id',)
        unique_together = ('cp_output_config', 'checklist_item')

    def __str__(self):
        return '{}: {}'.format(self.cp_output_config, self.checklist_item)


class PlannedCheckListItemPartnerInfo(models.Model):
    planned_checklist_item = models.ForeignKey(PlannedCheckListItem, verbose_name=_('Planned Checklist Item'),
                                               related_name='partners_info', on_delete=models.CASCADE)
    partner = models.ForeignKey('partners.PartnerOrganization', blank=True, null=True, verbose_name=_('Partner'),
                                on_delete=models.CASCADE)
    specific_details = models.TextField(verbose_name=_('Specific Details To Probe'), blank=True)
    standard_url = models.CharField(max_length=1000, verbose_name=_('URL To Standard'), blank=True)

    class Meta:
        verbose_name = _('Planned Checklist Item Partner Info')
        verbose_name_plural = _('Planned Checklist Items Partners Info')
        ordering = ('id',)
        unique_together = ('planned_checklist_item', 'partner')

    def __str__(self):
        return '{} info for {}'.format(self.partner, self.planned_checklist_item)
