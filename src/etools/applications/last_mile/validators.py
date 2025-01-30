
from etools.applications.last_mile.models import Transfer
from rest_framework.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

class TransferCheckOutValidator:

    def validate_destination_points(self, tranfer_type: str, destination_point):
        if tranfer_type not in [Transfer.WASTAGE, Transfer.DISPENSE, Transfer.HANDOVER] and not destination_point:
            raise ValidationError(_('Destination location is mandatory at checkout.'))