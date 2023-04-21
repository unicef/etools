from django.utils import timezone
from django.utils.translation import gettext as _

from rest_framework.exceptions import ValidationError


class EvidenceDescriptionValidator:
    def __call__(self, attrs):
        evidence = attrs.get("evidence")
        if evidence:
            if evidence.requires_description and not attrs.get("description"):
                raise ValidationError(_("Description is required."))


class PastDateValidator:
    def __call__(self, value):
        if value > timezone.now().date():
            raise ValidationError(_("Date may not be in the future"))
