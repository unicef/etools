from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import ugettext_lazy as _

from model_utils.models import TimeStampedModel
from ordered_model.models import OrderedModel

from etools.applications.field_monitoring.settings.models.checklist import CheckListItem
from etools.applications.field_monitoring.settings.models.methods import MethodType
from etools.applications.field_monitoring.shared.models import Method
from etools.applications.reports.models import ResultType


class CPOutputConfig(TimeStampedModel):
    cp_output = models.OneToOneField('reports.Result', related_name='fm_config',
                                     verbose_name=_('CP Output To Be Monitored'))
    is_monitored = models.BooleanField(default=True, verbose_name=_('Monitored At Community Level?'))
    is_priority = models.BooleanField(verbose_name=_('Priority?'), default=False)
    government_partners = models.ManyToManyField('partners.PartnerOrganization', blank=True,
                                                 verbose_name=_('Contributing Government Partners'))
    recommended_method_types = models.ManyToManyField(MethodType, blank=True, verbose_name=_('Method(s)'))

    def __str__(self):
        if self.cp_output.result_type.name == ResultType.OUTPUT:
            return self.cp_output.output_name
        return self.cp_output.result_name

    @staticmethod
    def clean_cp_ouput(cp_otput):
        if cp_otput.result_type.name != ResultType.OUTPUT:
            raise ValidationError(_('Incorrect CP Output provided.'))

    def clean(self):
        super().clean()
        self.clean_cp_ouput(self.cp_output)


class PlannedCheckListItem(OrderedModel):
    checklist_item = models.ForeignKey(CheckListItem, verbose_name=_('Checklist Item'))
    cp_output_config = models.ForeignKey(CPOutputConfig, verbose_name=_('CP Output Config'),
                                         related_name='planned_checklist_items')
    methods = models.ManyToManyField(Method, blank=True, verbose_name=_('Method(s)'))

    class Meta:
        unique_together = ('cp_output_config', 'checklist_item')

    def __str__(self):
        return '{}: {}'.format(self.cp_output_config, self.checklist_item)


class PlannedCheckListItemPartnerInfo(models.Model):
    planned_checklist_item = models.ForeignKey(PlannedCheckListItem, verbose_name=_('Planned Checklist Item'),
                                               related_name='partners_info')
    partner = models.ForeignKey('partners.PartnerOrganization', blank=True, null=True, verbose_name=_('Partner'))
    specific_details = models.TextField(verbose_name=_('Specific Details To Probe'), blank=True)
    standard_url = models.CharField(max_length=1000, verbose_name=_('URL To Standard'), blank=True)

    class Meta:
        unique_together = ('planned_checklist_item', 'partner')

    def __str__(self):
        return '{} info for {}'.format(self.partner, self.planned_checklist_item)
