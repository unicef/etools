import re

from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _


def uppercase_forbidden_validator(value):
    if re.findall('[A-Z]', value):
        raise ValidationError(_("Uppercase chars forbidden."), code='uppercase_forbidden')
