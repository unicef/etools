from django.http import HttpResponseForbidden
from django.urls import reverse

from rest_framework.exceptions import ValidationError
from unicef_notification.utils import send_notification_with_template

from etools.applications.partners.models import Intervention
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


class PMPInterventionAcceptReviewView(PMPInterventionMixin, InterventionDetailAPIView):
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
                template_name='partners/intervention/unicef_accepted_review',
                context=context
            )

        return response


class PMPInterventionReviewView(PMPInterventionMixin, InterventionDetailAPIView):
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


class PMPInterventionCancelView(PMPInterventionMixin, InterventionDetailAPIView):
    def update(self, request, *args, **kwargs):
        if self.is_partner_staff():
            return HttpResponseForbidden()
        pd = self.get_object()
        if pd.status == Intervention.CANCELLED:
            raise ValidationError("PD has already been cancelled.")
        request.data.clear()
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
                template_name='partners/intervention/unicef_cancel',
                context=context
            )

        return response


class PMPInterventionTerminateView(PMPInterventionMixin, InterventionDetailAPIView):
    def update(self, request, *args, **kwargs):
        if self.is_partner_staff():
            return HttpResponseForbidden()
        pd = self.get_object()
        if pd.status == Intervention.TERMINATED:
            raise ValidationError("PD has already been terminated.")

        # copy aross attachment doc id and in_amendment flag if present
        termination_doc = request.data.get("termination_doc_attachment")
        end = request.data.get("end")
        request.data.clear()
        request.data.update({"status": Intervention.TERMINATED})
        if termination_doc:
            request.data["termination_doc_attachment"] = termination_doc
        if end:
            request.data["end"] = end
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


class PMPInterventionSignatureView(PMPInterventionMixin, InterventionDetailAPIView):
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


class PMPInterventionUnlockView(PMPInterventionMixin, InterventionDetailAPIView):
    def update(self, request, *args, **kwargs):
        pd = self.get_object()
        request.data.clear()
        if self.is_partner_staff():
            if not pd.partner_accepted:
                raise ValidationError("PD is already unlocked.")
            request.data.update({"partner_accepted": False})
            recipients = [u.email for u in pd.unicef_focal_points.all()]
            template_name = 'partners/intervention/partner_unlocked'
        else:
            if not pd.unicef_accepted:
                raise ValidationError("PD is already unlocked.")
            request.data.update({"unicef_accepted": False})
            recipients = [u.email for u in pd.partner_focal_points.all()]
            template_name = 'partners/intervention/unicef_unlocked'

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


class PMPInterventionSendToPartnerView(PMPInterventionMixin, InterventionDetailAPIView):
    def update(self, request, *args, **kwargs):
        pd = self.get_object()
        if not pd.unicef_court:
            raise ValidationError("PD is currently with Partner")
        request.data.clear()
        request.data.update({"unicef_court": False})

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


class PMPInterventionSendToUNICEFView(PMPInterventionMixin, InterventionDetailAPIView):
    def update(self, request, *args, **kwargs):
        pd = self.get_object()
        if pd.unicef_court:
            raise ValidationError("PD is currently with UNICEF")
        request.data.clear()
        request.data.update({"unicef_court": True})

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
