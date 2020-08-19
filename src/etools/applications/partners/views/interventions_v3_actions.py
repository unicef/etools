from django.urls import reverse

from rest_framework.exceptions import ValidationError
from unicef_notification.utils import send_notification_with_template

from etools.applications.partners.views.interventions_v3 import InterventionDetailAPIView, PMPInterventionMixin


class PMPInterventionAcceptView(PMPInterventionMixin, InterventionDetailAPIView):
    def update(self, request, *args, **kwargs):
        pd = self.get_object()
        request.data.clear()
        if self.is_partner_staff():
            if pd.partner_accepted:
                raise ValidationError("Partner has already accepted this PD.")
            request.data.update({"partner_accepted": True})
            recipients = [u.email for u in pd.unicef_focal_points.all()]
            template_name = 'partners/intervention/partner_accepted'
        else:
            if pd.unicef_accepted:
                raise ValidationError("UNICEF has already accepted this PD.")
            request.data.update({"unicef_accepted": True})
            recipients = [u.email for u in pd.partner_focal_points.all()]
            template_name = 'partners/intervention/unicef_accepted'

        # send notification
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
            template_name=template_name,
            context=context
        )

        return super().update(request, *args, **kwargs)
