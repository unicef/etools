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

    def clean(self):
        if self.implementing_partner and self.partnership \
                and self.partnership.agreement.partner != self.implementing_partner:
            raise ValidationError(_('Partnership must be concluded with {partner}.').format(
                partner=self.implementing_partner
            ))

        if self.cp_output and self.partnership and self.cp_output.intervention_links.intervention != self.partnership:
            raise ValidationError(_('CP Output should be within the {partnership}.').format(
                partnership=self.partnership
            ))
