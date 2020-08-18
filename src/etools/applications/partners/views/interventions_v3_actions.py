from django.urls import reverse

from rest_framework.exceptions import ValidationError
from unicef_notification.utils import send_notification_with_template

from etools.applications.partners.views.interventions_v3 import InterventionDetailAPIView, PMPInterventionMixin


class PMPInterventionSendToPartnerView(PMPInterventionMixin, InterventionDetailAPIView):
    def update(self, request, *args, **kwargs):
        pd = self.get_object()
        if not pd.unicef_court:
            raise ValidationError("PD is currently with Partner")
        request.data.clear()
        request.data.update({"unicef_court": False})

        # notify partner
        recipients = [u.email for u in pd.partner_focal_points.all()]
        context = {
            "reference_number": pd.reference_number,
            "partner_name": str(pd.agreement.partner),
            "pd_link": reverse(
                "pmp_v3:intervention-detail",
                args=[pd.pk]
            ),
        }
        send_notification_with_template(
            recipients=recipients,
            template_name='partners/intervention/send_to_partner',
            context=context
        )

        return super().update(request, *args, **kwargs)


class PMPInterventionSendToUNICEFView(PMPInterventionMixin, InterventionDetailAPIView):
    def update(self, request, *args, **kwargs):
        pd = self.get_object()
        if pd.unicef_court:
            raise ValidationError("PD is currently with UNICEF")
        request.data.clear()
        request.data.update({"unicef_court": True})

        # notify unicef
        recipients = [u.email for u in pd.unicef_focal_points.all()]
        context = {
            "reference_number": pd.reference_number,
            "partner_name": str(pd.agreement.partner),
            "pd_link": reverse(
                "pmp_v3:intervention-detail",
                args=[pd.pk]
            ),
        }
        send_notification_with_template(
            recipients=recipients,
            template_name='partners/intervention/send_to_unicef',
            context=context
        )

        return super().update(request, *args, **kwargs)
