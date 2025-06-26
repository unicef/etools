from dataclasses import dataclass
from typing import Any, Dict, List

from etools.applications.last_mile import models


@dataclass
class IngestResultDTO:
    created_count: int
    skipped_existing_in_db: List[str]
    skipped_duplicate_in_payload: List[str]


class MaterialIngestService:

    def ingest_materials(self, validated_data: List[Dict[str, Any]]) -> IngestResultDTO:
        incoming_numbers = {item['number'] for item in validated_data}

        existing_numbers = set(
            models.Material.objects.filter(number__in=incoming_numbers).values_list('number', flat=True)
        )
        materials_to_create = []
        processed_numbers = set()
        skipped_due_to_db_duplicate = []
        skipped_due_to_payload_duplicate = []

        for material_data in validated_data:
            number = material_data['number']

            if number in existing_numbers:
                skipped_due_to_db_duplicate.append(number)
                continue

            if number in processed_numbers:
                skipped_due_to_payload_duplicate.append(number)
                continue

            materials_to_create.append(models.Material(**material_data))
            processed_numbers.add(number)

        if materials_to_create:
            models.Material.objects.bulk_create(materials_to_create)

        return IngestResultDTO(
            created_count=len(materials_to_create),
            skipped_existing_in_db=skipped_due_to_db_duplicate,
            skipped_duplicate_in_payload=skipped_due_to_payload_duplicate
        )
