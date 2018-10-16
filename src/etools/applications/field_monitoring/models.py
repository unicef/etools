from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import ugettext_lazy as _

from django_extensions.db.fields import AutoSlugField

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


UNICEFUser = GroupWrapper(code='unicef_user',
                          name='UNICEF User')
