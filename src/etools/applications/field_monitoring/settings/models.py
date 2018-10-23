from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import ugettext_lazy as _

from django_extensions.db.fields import AutoSlugField
from unicef_locations.models import Location, GatewayType

from etools.applications.field_monitoring.shared.models import Method
from etools.applications.reports.models import ResultType
from etools.applications.utils.groups.wrappers import GroupWrapper


class MethodType(models.Model):
    method = models.ForeignKey(Method, verbose_name=_('Method'))
    name = models.CharField(verbose_name=_('Name'), max_length=300)
    slug = AutoSlugField(verbose_name=_('Slug'), populate_from='name')

    def __str__(self):
        return self.name

    @staticmethod
    def clean_method(method):
        if not method.is_types_applicable:
            raise ValidationError(_('Unable to add type for this Method'))

    def clean(self):
        super().clean()
        self.clean_method(self.method)


class Site(Location):
    # should be moved to unicef_locations later

    security_detail = models.TextField(verbose_name=_('Detail on Security'), blank=True)

    def save(self, *args, **kwargs):
        if not self.gateway_id:
            self.gateway = GatewayType.objects.get_or_create(name='Site')[0]
        return super().save(*args, **kwargs)

    @staticmethod
    def clean_parent(parent):
        if parent.children.exclude(gateway__name='Site').exists():
            raise ValidationError(_('A lower administrative level exists within the Parent Administrative Location '
                                    'that you selected. Choose the lowest administrative level available in the '
                                    'system.'))

    def clean(self):
        super().clean()
        self.clean_parent(self.parent)


class CPOutputConfig(models.Model):
    cp_output = models.OneToOneField('reports.Result', related_name='fm_config',
                                     verbose_name=_('CP Output To Be Monitored'))
    is_monitored = models.BooleanField(default=True, verbose_name=_('Monitored At Community Level?'))
    is_priority = models.BooleanField(verbose_name=_('Priority?'), default=False)
    government_partners = models.ManyToManyField('partners.PartnerOrganization', blank=True,
                                                 verbose_name=_('Contributing Government Partners'))

    def __str__(self):
        return self.cp_output.output_name

    @staticmethod
    def clean_cp_ouput(cp_otput):
        if cp_otput.result_type.name != ResultType.OUTPUT:
            raise ValidationError(_('Incorrect CP Output provided.'))

    def clean(self):
        super().clean()
        self.clean_cp_ouput(self.cp_output)


UNICEFUser = GroupWrapper(code='unicef_user',
                          name='UNICEF User')
