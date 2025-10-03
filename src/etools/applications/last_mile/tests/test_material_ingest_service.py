from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.last_mile import models
from etools.applications.last_mile.services_ext import MaterialIngestService
from etools.applications.last_mile.tests.factories import MaterialFactory


class TestMaterialIngestServiceCustomUOM(BaseTenantTestCase):

    def setUp(self):
        self.service = MaterialIngestService()

    def test_custom_uom_constants_defined(self):
        self.assertIn("S0000237", self.service.CUSTOM_UOM_OVERRIDES)
        self.assertIn("S0000236", self.service.CUSTOM_UOM_OVERRIDES)

        override_237 = self.service.CUSTOM_UOM_OVERRIDES["S0000237"]
        self.assertEqual(override_237["original_uom"], "CAR")
        self.assertEqual(override_237["other"]["uom_map"], {"CAN": 1, "CAR": 24})

        override_236 = self.service.CUSTOM_UOM_OVERRIDES["S0000236"]
        self.assertEqual(override_236["original_uom"], "CAR")
        self.assertEqual(override_236["other"]["uom_map"], {"CAN": 1, "CAR": 24})

    def test_new_material_with_custom_uom_override(self):
        validated_data = [
            {
                "number": "S0000237",
                "short_description": "Test Material 237",
                "original_uom": "EA",
                "other": None
            },
            {
                "number": "S0000236",
                "short_description": "Test Material 236",
                "original_uom": "BOX",
                "other": {"some_field": "value"}
            },
            {
                "number": "S0000999",
                "short_description": "Regular Material",
                "original_uom": "EA",
                "other": None
            }
        ]

        result = self.service.ingest_materials(validated_data)

        self.assertEqual(result.created_count, 3)
        self.assertEqual(len(result.skipped_existing_in_db), 0)

        material_237 = models.Material.objects.get(number="S0000237")
        self.assertEqual(material_237.original_uom, "CAR")
        self.assertEqual(material_237.other["uom_map"], {"CAN": 1, "CAR": 24})

        material_236 = models.Material.objects.get(number="S0000236")
        self.assertEqual(material_236.original_uom, "CAR")
        self.assertEqual(material_236.other["uom_map"], {"CAN": 1, "CAR": 24})
        self.assertEqual(material_236.other.get("some_field"), "value")

        material_999 = models.Material.objects.get(number="S0000999")
        self.assertEqual(material_999.original_uom, "EA")
        self.assertIsNone(material_999.other)

    def test_existing_material_updated_only_when_different(self):
        material_237_needs_update = MaterialFactory(
            number="S0000237",
            short_description="Material 237",
            original_uom="EA",
            other=None
        )

        material_236_already_correct = MaterialFactory(
            number="S0000236",
            short_description="Material 236",
            original_uom="CAR",
            other={"uom_map": {"CAN": 1, "CAR": 24}}
        )

        material_999_no_override = MaterialFactory(
            number="S0000999",
            short_description="Regular Material",
            original_uom="BOX",
            other={"custom": "data"}
        )

        validated_data = [
            {"number": "S0000237", "short_description": "New desc", "original_uom": "KG"},
            {"number": "S0000236", "short_description": "New desc", "original_uom": "KG"},
            {"number": "S0000999", "short_description": "New desc", "original_uom": "KG"}
        ]

        result = self.service.ingest_materials(validated_data)

        self.assertEqual(result.created_count, 0)
        self.assertEqual(len(result.skipped_existing_in_db), 3)

        material_237_needs_update.refresh_from_db()
        self.assertEqual(material_237_needs_update.original_uom, "CAR")
        self.assertEqual(material_237_needs_update.other["uom_map"], {"CAN": 1, "CAR": 24})

        material_236_already_correct.refresh_from_db()
        self.assertEqual(material_236_already_correct.original_uom, "CAR")
        self.assertEqual(material_236_already_correct.other["uom_map"], {"CAN": 1, "CAR": 24})

        material_999_no_override.refresh_from_db()
        self.assertEqual(material_999_no_override.original_uom, "BOX")
        self.assertEqual(material_999_no_override.other["custom"], "data")

    def test_partial_update_uom_map_only(self):
        material = MaterialFactory(
            number="S0000237",
            short_description="Material 237",
            original_uom="CAR",
            other={"uom_map": {"CAN": 2, "CAR": 12}, "extra": "field"}
        )

        validated_data = [
            {"number": "S0000237", "short_description": "desc", "original_uom": "EA"}
        ]

        self.service.ingest_materials(validated_data)
        material.refresh_from_db()
        self.assertEqual(material.original_uom, "CAR")
        self.assertEqual(material.other["uom_map"], {"CAN": 1, "CAR": 24})
        self.assertEqual(material.other["extra"], "field")

    def test_partial_update_original_uom_only(self):
        material = MaterialFactory(
            number="S0000236",
            short_description="Material 236",
            original_uom="EA",
            other={"uom_map": {"CAN": 1, "CAR": 24}}
        )

        validated_data = [
            {"number": "S0000236", "short_description": "desc", "original_uom": "BOX"}
        ]

        self.service.ingest_materials(validated_data)

        material.refresh_from_db()
        self.assertEqual(material.original_uom, "CAR")
        self.assertEqual(material.other["uom_map"], {"CAN": 1, "CAR": 24})

    def test_update_with_null_other_field(self):
        material = MaterialFactory(
            number="S0000237",
            short_description="Material 237",
            original_uom="EA",
            other=None
        )

        validated_data = [
            {"number": "S0000237", "short_description": "desc", "original_uom": "KG"}
        ]

        self.service.ingest_materials(validated_data)

        material.refresh_from_db()
        self.assertEqual(material.original_uom, "CAR")
        self.assertIsNotNone(material.other)
        self.assertEqual(material.other["uom_map"], {"CAN": 1, "CAR": 24})

    def test_no_update_when_already_correct(self):
        material = MaterialFactory(
            number="S0000236",
            short_description="Material 236",
            original_uom="CAR",
            other={"uom_map": {"CAN": 1, "CAR": 24}, "existing": "data"}
        )

        original_modified = material.modified

        validated_data = [
            {"number": "S0000236", "short_description": "desc", "original_uom": "EA"}
        ]

        self.service.ingest_materials(validated_data)

        material.refresh_from_db()
        self.assertEqual(material.modified, original_modified)
        self.assertEqual(material.original_uom, "CAR")
        self.assertEqual(material.other["uom_map"], {"CAN": 1, "CAR": 24})
        self.assertEqual(material.other["existing"], "data")
