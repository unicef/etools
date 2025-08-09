from etools.applications.last_mile.models import Material
from etools.applications.partners.models import Organization


class ValidatorEXT:

    def validate_organization(self, vendor_number):
        try:
            organization = Organization.objects.select_related('partner').get(vendor_number=vendor_number)
            if not hasattr(organization, 'partner'):
                raise ValueError(f"No partner available for vendor {vendor_number}")
            return organization
        except (Organization.DoesNotExist, ValueError):
            raise ValueError("Organization not found by vendor number")


class ItemValidator:
    def __init__(self, all_materials, existing_item_ids):
        self.all_materials = all_materials
        self.existing_item_ids = existing_item_ids

    def validate(self, item_data, processed_ids_in_run):
        material_number = item_data.get('material_number')
        material = self.all_materials.get(material_number)
        uom = item_data.get('uom')
        allowed_uoms = [uom[0] for uom in Material.UOM]
        if uom not in allowed_uoms:
            return None, f"UOM '{uom}' not valid."
        if not material:
            return None, f"Material number '{material_number}' not found."

        item_id = item_data.get('other', {}).get('itemid')
        if not item_id:
            return None, "Item ID is missing from payload."

        if item_id in self.existing_item_ids:
            return None, "Duplicate item found in database."

        if item_id in processed_ids_in_run:
            return None, "Duplicate item found within the same payload."

        return material, None
