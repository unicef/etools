from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

from rest_framework.exceptions import ValidationError

from etools.applications.last_mile.admin_panel.constants import (
    EMAIL_NOT_PROVIDED,
    GROUP_DOES_NOT_EXIST,
    GROUP_NOT_AVAILABLE,
    GROUP_NOT_PROVIDED,
    INVALID_QUANTITY,
    ITEMS_NOT_PROVIDED,
    LAST_MILE_PROFILE_NOT_FOUND,
    ORGANIZATION_DOES_NOT_EXIST,
    PARTNER_NOT_UNDER_LOCATION,
    PARTNER_NOT_UNDER_ORGANIZATION,
    POI_TYPE_ALREADY_EXISTS,
    REALM_ALREADY_EXISTS,
    STATUS_NOT_CRRECT,
    TRANSFER_HAS_NO_ITEMS,
    TRANSFER_NOT_FOUND_FOR_REVERSE,
    TRANSFER_TYPE_HANDOVER_NOT_ALLOWED,
    UOM_NOT_PROVIDED,
    UOM_NOT_VALID,
    USER_DOES_NOT_EXIST,
    USER_NOT_PROVIDED,
)
from etools.applications.last_mile.models import Item, Material, PointOfInterest, PointOfInterestType, Profile, Transfer
from etools.applications.partners.models import PartnerOrganization
from etools.applications.users.models import Country, Group, Realm, User


class AdminPanelValidator:

    def validate_poi_type(self, poi_type_name: str) -> None:
        if PointOfInterestType.objects.filter(name=poi_type_name).exists():
            raise ValidationError(_(POI_TYPE_ALREADY_EXISTS))

    def validate_user_email(self, user_email: str) -> None:
        if not get_user_model().objects.filter(email=user_email).exists():
            raise ValidationError(_(USER_DOES_NOT_EXIST))

    def validate_group_name(self, group: Group, available_groups: list) -> None:
        if group.name not in available_groups:
            raise ValidationError(_(GROUP_NOT_AVAILABLE))
        if not Group.objects.filter(name=group.name).exists():
            raise ValidationError(_(GROUP_DOES_NOT_EXIST))

    def validate_input_data(self, data: dict) -> None:
        if not data.get('user'):
            raise ValidationError(_(USER_NOT_PROVIDED))
        if not data.get('group'):
            raise ValidationError(_(GROUP_NOT_PROVIDED))
        if not data.get('user', {}).get('email'):
            raise ValidationError(_(EMAIL_NOT_PROVIDED))

    def validate_realm(self, user: User, country: Country, group: Group) -> None:
        if Realm.objects.filter(user=user, country=country, group=group, organization=user.profile.organization).exists():
            raise ValidationError(_(REALM_ALREADY_EXISTS))

    def validate_profile(self, user: User) -> None:
        if not getattr(user.profile, 'organization', None):
            raise ValidationError(_(ORGANIZATION_DOES_NOT_EXIST))
        if not getattr(user.profile.organization, 'partner', None):
            raise ValidationError(_(PARTNER_NOT_UNDER_ORGANIZATION))

    def validate_last_mile_profile(self, user: User) -> None:
        if not getattr(user, 'last_mile_profile', None):
            raise ValidationError(_(LAST_MILE_PROFILE_NOT_FOUND))

    def validate_status(self, status: str) -> None:
        if status not in [Profile.ApprovalStatus.APPROVED, Profile.ApprovalStatus.REJECTED]:
            raise ValidationError(_(STATUS_NOT_CRRECT))

    def validate_items(self, items: list):
        uom_types = [uom[0] for uom in Material.UOM]
        if not items:
            raise ValidationError(_(ITEMS_NOT_PROVIDED))
        for item in items:
            if item.get('quantity', 0) < 1:
                raise ValidationError(_(INVALID_QUANTITY))
            uom = item.get('uom')
            if not uom:
                raise ValidationError(_(UOM_NOT_PROVIDED))
            if uom not in uom_types:
                raise ValidationError(_(UOM_NOT_VALID))

    def validate_partner_location(self, location: PointOfInterest, partner: PartnerOrganization):
        if partner not in location.partner_organizations.all():
            raise ValidationError(_(PARTNER_NOT_UNDER_LOCATION))

    def validate_reverse_transfer(self, transfer: Transfer | None):
        if not transfer:
            raise ValidationError(_(TRANSFER_NOT_FOUND_FOR_REVERSE))

    def validate_transfer_items(self, transfer: Transfer):
        items = Item.all_objects.filter(transfer=transfer)
        if not items:
            raise ValidationError(_(TRANSFER_HAS_NO_ITEMS))

    def validate_transfer_type(self, transfer: Transfer):
        if transfer.transfer_type == Transfer.HANDOVER:
            raise ValidationError(_(TRANSFER_TYPE_HANDOVER_NOT_ALLOWED))
