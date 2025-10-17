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
            'errors': [],
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
                result['errors'].append({'id': intervention.id, 'errors': str(exc)})

        return result
