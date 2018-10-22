from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import ugettext_lazy as _

from django_extensions.db.fields import AutoSlugField
from unicef_locations.models import Location, GatewayType

from etools.applications.field_monitoring_shared.models import Method
from etools.applications.utils.groups.wrappers import GroupWrapper


class MethodType(models.Model):
    method = models.ForeignKey(Method, verbose_name=_('Method'))
    name = models.CharField(verbose_name=_('Name'), max_length=300)
    slug = AutoSlugField(verbose_name=_('Slug'), populate_from='name')
    is_recommended = models.BooleanField(verbose_name=_('Is Recommended'), default=False)

    def __str__(self):
        return self.name

    def clean(self):
        if not self.method.is_types_applicable:
            raise ValidationError(_('Unable to add type for this Method'))


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
        type(self).clean_parent(self.parent)


UNICEFUser = GroupWrapper(code='unicef_user',
                          name='UNICEF User')
