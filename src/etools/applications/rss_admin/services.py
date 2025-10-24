from typing import Iterable

from etools_validator.exceptions import TransitionError

from etools.applications.partners.models import Intervention
from etools.applications.partners.validation.interventions import transition_to_closed


class ProgrammeDocumentService:

    @staticmethod
    def bulk_close(interventions: Iterable[Intervention]) -> dict:
        """Close PDs in bulk.

        Accepts an iterable of Intervention instances and attempts to close each one
        according to the same business rules used elsewhere. Returns a dict with
        'closed_ids' and 'errors' arrays, preserving the existing API contract.
        """
        result = {
            'closed_ids': [],
            'errors': [],  # legacy per-item list of errors with id and errors
        }

        for intervention in interventions:
            # Only allow closing from ENDED status
            if intervention.status != Intervention.ENDED:
                result['errors'].append({'id': intervention.id, 'errors': ['PD is not in ENDED status']})
                continue
            try:
                transition_to_closed(intervention)
                intervention.status = Intervention.CLOSED
                intervention.save()
                result['closed_ids'].append(intervention.id)
            except TransitionError as exc:
                # TransitionError from validators may be a list-like message; normalize to list of strings
                message = str(exc)
                # Some validators raise with a list inside; DRF usually stringifies to "['msg']". Keep as string.
                result['errors'].append({'id': intervention.id, 'errors': [message] if not isinstance(message, list) else message})

        # Group errors by error message to reduce payload size for many IDs
        if result['errors']:
            grouped = {}
            for item in result['errors']:
                err_list = item.get('errors') or []
                # take the first error text as the grouping key for simplicity
                key = err_list[0] if err_list else 'Unknown error'
                if key not in grouped:
                    grouped[key] = []
                grouped[key].append(item['id'])
            result['grouped_errors'] = [{'message': k, 'ids': v} for k, v in grouped.items()]

        return result
