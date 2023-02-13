import logging

from django.db import connection

from etools.applications.organizations.models import Organization
from etools.applications.tpm.tpmpartners.models import TPMPartner
from etools.applications.users.mixins import TPM_ACTIVE_GROUPS
from etools.applications.users.models import Country, Realm
from etools.applications.vision.synchronizers import VisionDataTenantSynchronizer

logger = logging.getLogger(__name__)


class TPMPartnerSynchronizer(VisionDataTenantSynchronizer):
    GLOBAL_CALL = True
    ENDPOINT = 'partners'
    REQUIRED_KEYS = (
        "VENDOR_CODE",
        "VENDOR_NAME",
    )

    MAPPING = {
        "vendor_number": "VENDOR_CODE",
        "name": "VENDOR_NAME",
        "street_address": "STREET",
        "city": "CITY",
        "postal_code": "POSTAL_CODE",
        "country": "COUNTRY",
        "email": "EMAIL",
        "phone_number": "PHONE_NUMBER",
        "blocked": "POSTING_BLOCK",
        "deleted_flag": "MARKED_FOR_DELETION",
    }

    def _partner_save(self, partner):
        processed = 0

        try:
            organization, _ = Organization.objects.update_or_create(
                vendor_number=partner['VENDOR_CODE'],
                defaults={
                    'name': partner['VENDOR_NAME'],
                }
            )
            defaults = {
                'street_address': partner['STREET'] if partner['STREET'] else '',
                'city': partner['CITY'] if partner['CITY'] else '',
                'postal_code': partner['POSTAL_CODE'] if partner["POSTAL_CODE"] else '',
                'country': partner['COUNTRY'] if partner['COUNTRY'] else '',
                'email': partner['EMAIL'] if partner['EMAIL'] else '',
                'phone_number': partner['PHONE_NUMBER'] if partner['PHONE_NUMBER'] else '',
                'vision_synced': True,
                'blocked': True if partner['POSTING_BLOCK'] else False,
                'deleted_flag': True if partner['MARKED_FOR_DELETION'] else False,
                'hidden': True if partner['POSTING_BLOCK'] or partner['MARKED_FOR_DELETION'] else False,
            }
            partner, _ = TPMPartner.objects.update_or_create(organization=organization, defaults=defaults)

            country = Country.objects.get(schema_name=defaults['country'] if defaults['country'] else connection.tenant.schema_name)
            partner.countries.add(country)

            if partner.deleted_flag:
                self.deactivate_staff_members(partner)
            processed = 1

        except Exception:
            logger.exception('Exception occurred during Partner Sync')

        return processed

    def _convert_records(self, records):
        return [records['ROWSET']['ROW']]

    def _filter_records(self, records):
        records = super()._filter_records(records)

        def bad_record(record):
            if not record['VENDOR_NAME']:
                return False
            return True

        return [rec for rec in records if bad_record(rec)]

    def _save_records(self, records):
        processed = 0
        filtered_records = self._filter_records(records)

        for partner in filtered_records:
            processed += self._partner_save(partner)

        return processed

    @staticmethod
    def deactivate_staff_members(partner):
        # TODO: REALMS - do cleanup
        # staff_members = partner.staff_members.all()
        # # deactivate the users
        # users_deactivate = User.objects.filter(tpmpartners_tpmpartnerstaffmember__in=staff_members)
        # users_deactivate.update(is_active=False)
        try:
            Realm.objects.filter(
                country__in=partner.countries.all(),
                organization=partner.organization,
                group__name__in=TPM_ACTIVE_GROUPS,
            ).update(is_active=False)
        except Country.DoesNotExist:
            logging.error(f"No country with name {partner.country} exists. "
                          f"Cannot deactivate realms for users.")
