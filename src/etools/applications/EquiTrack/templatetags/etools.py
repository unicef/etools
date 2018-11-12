from django import template
from django.utils.safestring import mark_safe

from etools import NAME, VERSION

register = template.Library()


@register.simple_tag
def etools_version():
    return mark_safe('{}: v{}'.format(NAME, VERSION))
