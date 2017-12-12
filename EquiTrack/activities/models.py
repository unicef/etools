from __future__ import absolute_import, division, print_function, unicode_literals

from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import ugettext_lazy as _

from model_utils.managers import InheritanceManager


class Activity(models.Model):
    partner = models.ForeignKey('partners.PartnerOrganization', verbose_name=_('Implementing Partner'), null=True)
    intervention = models.ForeignKey('partners.Intervention', verbose_name=_('Intervention'), null=True)
    cp_output = models.ForeignKey('reports.Result', verbose_name=_('CP Output'),
                                  null=True, blank=True)
    locations = models.ManyToManyField('locations.Location', verbose_name=_('Locations'), related_name='+')
    date = models.DateField(verbose_name=_('Date'), blank=True, null=True)

    objects = InheritanceManager()

    @staticmethod
    def _validate_intervention(partner, intervention):
        if partner and intervention and intervention.agreement.partner != partner:
            raise ValidationError(_('Intervention must be concluded with {partner}.').format(
                partner=partner
            ))

    @staticmethod
    def _validate_cp_output(intervention, cp_output):
        if cp_output and intervention and cp_output.intervention_links.intervention != intervention:
            raise ValidationError(_('CP Output should be within the {intervention}.').format(
                intervention=intervention
            ))

    def clean(self):
        self._validate_intervention(self.partner, self.intervention)
        self._validate_cp_output(self.intervention, self.cp_output)
