
from django.utils.translation import gettext_lazy as _

from rest_framework.exceptions import ValidationError

from etools.applications.last_mile.models import Transfer


class TransferCheckOutValidator:

    def validate_destination_points(self, tranfer_type: str, destination_point: int) -> None:
        if tranfer_type not in [Transfer.WASTAGE, Transfer.DISPENSE, Transfer.HANDOVER] and not destination_point:
            raise ValidationError(_('Destination location is mandatory at checkout.'))

    def validate_proof_file(self, proof_file: int) -> None:
        if not proof_file:
            raise ValidationError(_('The proof file is required.'))

    def validate_handover(self, transfer_type: str, partner_id: int) -> None:
        if transfer_type == Transfer.HANDOVER and not partner_id:
            raise ValidationError(_('A Handover to a partner requires a partner id.'))
