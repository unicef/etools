from django.utils.translation import ugettext as _

from rest_framework.exceptions import ValidationError


class AttachmentRequiresFileOrLink:
    def __init__(self, base):
        self.base = base

        if bool(base.get("file")) == bool(base.get("hyperlink")):
            raise ValidationError(_('Please provide file or hyperlink.'))
