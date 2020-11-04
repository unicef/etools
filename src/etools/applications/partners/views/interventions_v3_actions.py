from django.http import HttpResponseForbidden
from django.urls import reverse
from django.utils import timezone

from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from unicef_notification.utils import send_notification_with_template

from etools.applications.partners.models import Intervention, PartnerStaffMember
from etools.applications.partners.serializers.interventions_v3 import InterventionDetailSerializer
from etools.applications.partners.views.interventions_v3 import InterventionDetailAPIView, PMPInterventionMixin


class PMPInterventionActionView(PMPInterventionMixin, InterventionDetailAPIView):
    def update(self, request, *args, **kwargs):
        response = super().update(request, *args, **kwargs)
        # need to overwrite successful response, so we get v3 serializer
        if response.status_code == 200:
            response = Response(
                InterventionDetailSerializer(
                    self.instance,
                    context=self.get_serializer_context(),
                ).data,
            )
        return response

    def is_partner_focal_point(self, pd):
        psm = self.request.user.partner_staff_member
        if psm is None:
            return False
        return psm in pd.partner_focal_points.all()


class PMPInterventionAcceptView(PMPInterventionActionView):
    def update(self, request, *args, **kwargs):
        pd = self.get_object()
        request.data.clear()
        if pd.status not in [Intervention.DRAFT]:
            raise ValidationError("Action is not allowed")
        if self.is_partner_staff():
            if not self.is_partner_focal_point(pd):
                raise ValidationError("You need to be a focal point in order to perform this action")
            if pd.partner_accepted:
                raise ValidationError("Partner has already accepted this PD.")
            if pd.unicef_court:
                raise ValidationError("You cannot perform this action while the PD "
                                      "is not available for partner to edit")
            # When accepting on behalf of the partner since there is no further action, it will automatically
            # be sent to unicef
            request.data.update({"partner_accepted": True, "unicef_court": True})
            recipients = [u.email for u in pd.unicef_focal_points.all()]
            template_name = 'partners/intervention/partner_accepted'
        else:
            if not pd.unicef_court:
                raise ValidationError("You cannot perform this action while the PD "
                                      "is not available for UNICEF to edit")

            if pd.unicef_accepted:
                raise ValidationError("UNICEF has already accepted this PD.")

            if self.request.user not in pd.unicef_focal_points.all():
                raise ValidationError("Only focal points can accept")

            request.data.update({"unicef_accepted": True})
            recipients = [u.email for u in pd.partner_focal_points.all()]
            template_name = 'partners/intervention/unicef_accepted'

        response = super().update(request, *args, **kwargs)

        if response.status_code == 200:
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

        return response


class PMPInterventionAcceptReviewView(PMPInterventionActionView):
    def update(self, request, *args, **kwargs):
        if self.is_partner_staff():
            return HttpResponseForbidden()
        pd = self.get_object()
        if pd.status == Intervention.REVIEW:
            raise ValidationError("PD is already in Review status.")
        request.data.clear()
        if not pd.unicef_accepted:
            request.data.update({"unicef_accepted": True})
        request.data.update({"status": Intervention.REVIEW})

        response = super().update(request, *args, **kwargs)

        if response.status_code == 200:
            # send notification
            recipients = [
                u.email for u in pd.partner_focal_points.all()
            ] + [
                u.email for u in pd.unicef_focal_points.all()
            ]
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
                template_name='partners/intervention/unicef_accepted_reviewed',
                context=context
            )

        return response


class PMPInterventionReviewView(PMPInterventionActionView):
    def update(self, request, *args, **kwargs):
        if self.is_partner_staff():
            return HttpResponseForbidden()
        pd = self.get_object()
        if pd.status == Intervention.REVIEW:
            raise ValidationError("PD is already in Review status.")
        request.data.clear()
        request.data.update({"status": Intervention.REVIEW})

        response = super().update(request, *args, **kwargs)

        if response.status_code == 200:
            # send notification
            recipients = [
                u.email for u in pd.partner_focal_points.all()
            ] + [
                u.email for u in pd.unicef_focal_points.all()
            ]
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
                template_name='partners/intervention/unicef_reviewed',
                context=context
            )

        return response


class PMPInterventionCancelView(PMPInterventionActionView):
    def update(self, request, *args, **kwargs):
        if self.is_partner_staff():
            return HttpResponseForbidden()
        pd = self.get_object()
        if pd.status == Intervention.CANCELLED:
            raise ValidationError("PD has already been cancelled.")
        request.data.update({"status": Intervention.CANCELLED})

        response = super().update(request, *args, **kwargs)

        if response.status_code == 200:
            # send notification
            recipients = [
                u.email for u in pd.partner_focal_points.all()
            ] + [
                u.email for u in pd.unicef_focal_points.all()
            ]
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
                template_name='partners/intervention/unicef_cancelled',
                context=context
            )

        return response


class PMPInterventionTerminateView(PMPInterventionActionView):
    def update(self, request, *args, **kwargs):
        if self.is_partner_staff():
            return HttpResponseForbidden()
        pd = self.get_object()
        if pd.status == Intervention.TERMINATED:
            raise ValidationError("PD has already been terminated.")

        # override status as terminated
        request.data.update({"status": Intervention.TERMINATED})
        response = super().update(request, *args, **kwargs)

        if response.status_code == 200:
            # send notification
            recipients = [
                u.email for u in pd.partner_focal_points.all()
            ] + [
                u.email for u in pd.unicef_focal_points.all()
            ]
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
                template_name='partners/intervention/unicef_terminated',
                context=context
            )

        return response


class PMPInterventionSignatureView(PMPInterventionActionView):
    def update(self, request, *args, **kwargs):
        if self.is_partner_staff():
            return HttpResponseForbidden()
        pd = self.get_object()
        if pd.status == Intervention.SIGNATURE:
            raise ValidationError("PD is already in Signature status.")
        request.data.clear()
        request.data.update({"status": Intervention.SIGNATURE})

        response = super().update(request, *args, **kwargs)

        if response.status_code == 200:
            # send notification
            recipients = [
                u.email for u in pd.partner_focal_points.all()
            ] + [
                u.email for u in pd.unicef_focal_points.all()
            ]
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
                template_name='partners/intervention/unicef_signature',
                context=context
            )

        return response


class PMPInterventionUnlockView(PMPInterventionActionView):
    def update(self, request, *args, **kwargs):
        pd = self.get_object()
        request.data.clear()
        if not pd.locked:
            raise ValidationError("PD is already unlocked.")

        if self.is_partner_staff():
            recipients = [u.email for u in pd.unicef_focal_points.all()]
            template_name = 'partners/intervention/partner_unlocked'
        else:
            recipients = [u.email for u in pd.partner_focal_points.all()]
            template_name = 'partners/intervention/unicef_unlocked'

        request.data.update({"partner_accepted": False, "unicef_accepted": False})
        response = super().update(request, *args, **kwargs)

        if response.status_code == 200:
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

        return response


class PMPInterventionSendToPartnerView(PMPInterventionActionView):
    def update(self, request, *args, **kwargs):
        pd = self.get_object()
        if not pd.unicef_court:
            raise ValidationError("PD is currently with Partner")
        request.data.clear()
        request.data.update({"unicef_court": False})
        if not pd.date_sent_to_partner:
            request.data.update({
                "date_sent_to_partner": timezone.now().strftime("%Y-%m-%d"),
            })

        response = super().update(request, *args, **kwargs)

        if response.status_code == 200:
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

        return response


class PMPInterventionSendToUNICEFView(PMPInterventionActionView):
    def update(self, request, *args, **kwargs):
        pd = self.get_object()
        if pd.unicef_court:
            raise ValidationError("PD is currently with UNICEF")
        request.data.clear()
        request.data.update({"unicef_court": True})
        if not pd.date_draft_by_partner:
            request.data.update({
                "date_draft_by_partner": timezone.now().strftime("%Y-%m-%d"),
            })

        response = super().update(request, *args, **kwargs)

        if response.status_code == 200:
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

        return response
