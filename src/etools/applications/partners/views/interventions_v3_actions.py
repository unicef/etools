from rest_framework.exceptions import ValidationError

from etools.applications.partners.views.interventions_v3 import InterventionDetailAPIView, PMPInterventionMixin


class PMPInterventionSendToPartnerView(PMPInterventionMixin, InterventionDetailAPIView):
    def update(self, request, *args, **kwargs):
        pd = self.get_object()
        if not pd.unicef_court:
            raise ValidationError("PD is currently with Partner")
        request.data.clear()
        request.data.update({"unicef_court": False})
        return super().update(request, *args, **kwargs)


class PMPInterventionSendToUNICEFView(PMPInterventionMixin, InterventionDetailAPIView):
    def update(self, request, *args, **kwargs):
        pd = self.get_object()
        if pd.unicef_court:
            raise ValidationError("PD is currently with UNICEF")
        request.data.clear()
        request.data.update({"unicef_court": True})
        return super().update(request, *args, **kwargs)
