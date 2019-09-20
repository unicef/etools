from django.utils.translation import ugettext_lazy as _

from rest_framework.exceptions import ValidationError


class EvidenceDescriptionValidator:
    def __call__(self, attrs):
        evidence = attrs.get("evidence")
        if evidence:
            if evidence.requires_description and not attrs.get("description"):
                raise ValidationError(_("Description is required."))
