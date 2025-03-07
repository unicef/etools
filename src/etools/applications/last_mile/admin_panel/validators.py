from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

from rest_framework.exceptions import ValidationError

from etools.applications.last_mile.models import Material, PointOfInterest, PointOfInterestType
from etools.applications.partners.models import PartnerOrganization
from etools.applications.users.models import Group, Realm


class AdminPanelValidator:

    def validate_poi_type(self, value: str):
        if PointOfInterestType.objects.filter(name=value).exists():
            raise ValidationError({"message": _("Poi type already exists")})

    def validate_user_email(self, value: str):
        if not get_user_model().objects.filter(email=value).exists():
            raise ValidationError({"message": _("User not exist")})

    def validate_group_name(self, value, available_groups):
        if value.name not in available_groups:
            raise ValidationError({"message": _("Group not available")})
        if not Group.objects.filter(name=value.name).exists():
            raise ValidationError({"message": _("Group not exist")})

    def validate_input_data(self, data: dict):
        if not data.get('user'):
            raise ValidationError({"message": _("User not sent")})
        if not data.get('group'):
            raise ValidationError({"message": _("Group not sent")})
        if not data.get('user', {}).get('email'):
            raise ValidationError({"message": _("Email not sent")})

    def validate_realm(self, user, country, group):
        if Realm.objects.filter(user=user, country=country, group=group, organization=user.profile.organization).exists():
            raise ValidationError({"message": _("Realm already exist")})

    def validate_profile(self, obj):
        if not getattr(obj.profile, 'organization', None):
            raise ValidationError({"message": _("Organization not exist")})
        if not getattr(obj.profile.organization, 'partner', None):
            raise ValidationError({"message": _("Partner not exist under organization")})

    def validate_items(self, items: list):
        uom_types = [uom[0] for uom in Material.UOM]
        if not items:
            raise ValidationError({"message": _("Items not sent")})
        for item in items:
            if item.get('quantity', 0) < 1:
                raise ValidationError({"message": _("Quantity must be greater than 0")})
            uom = item.get('uom')
            if not uom:
                raise ValidationError({"message": _("UOM not sent")})
            if uom not in uom_types:
                raise ValidationError({"message": _("UOM not valid")})

    def validate_partner_location(self, location: PointOfInterest, partner: PartnerOrganization):
        if partner not in location.partner_organizations.all():
            raise ValidationError({"message": _("Partner not exist under location")})
