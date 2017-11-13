from __future__ import absolute_import, division, print_function, unicode_literals

from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import ugettext_lazy as _


class Activity(models.Model):
    implementing_partner = models.ForeignKey('partners.PartnerOrganization', verbose_name=_('Implementing Partner'),
                                             null=True)
    partnership = models.ForeignKey('partners.Intervention', verbose_name=_('partnership'), null=True)
    cp_output = models.ForeignKey('reports.Result', verbose_name=_('CP Output'),
                                  null=True, blank=True)
    locations = models.ManyToManyField('locations.Location', verbose_name=_('Locations'), related_name='+')
    date = models.DateField(verbose_name=_('Date'), blank=True, null=True)

    class Meta:
        abstract = True

    @staticmethod
    def _validate_partnership(implementing_partner, partnership):
        if implementing_partner and partnership and partnership.agreement.partner != implementing_partner:
            raise ValidationError(_('Partnership must be concluded with {partner}.').format(
                partner=implementing_partner
            ))

    @staticmethod
    def _validate_cp_output(partnership, cp_output):
        if cp_output and partnership and cp_output.intervention_links.intervention != partnership:
            raise ValidationError(_('CP Output should be within the {partnership}.').format(
                partnership=partnership
            ))

    def clean(self):
        self._validate_partnership(self.implementing_partner, self.partnership)
        self._validate_cp_output(self.partnership, self.cp_output)
