from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db import connection, transaction
from django.http import HttpResponseForbidden
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext as _

from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from etools.applications.environment.notifications import send_notification_with_template
from etools.applications.partners.amendment_utils import MergeError
from etools.applications.partners.models import Intervention, InterventionAmendment, InterventionReview
from etools.applications.partners.permissions import (
    IsInterventionBudgetOwnerPermission,
    PARTNERSHIP_MANAGER_GROUP,
    PRC_SECRETARY,
    user_group_permission,
    UserIsUnicefFocalPoint,
)
from etools.applications.partners.serializers.interventions_v3 import (
    AmendedInterventionReviewActionSerializer,
    InterventionDetailSerializer,
    InterventionReviewActionSerializer,
    InterventionReviewSendBackSerializer,
)
from etools.applications.partners.tasks import send_pd_to_vision
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
        return self.request.user in pd.partner_focal_points.all()

    def send_notification(self, pd, recipients, template_name, context):
        unicef_rec = [r for r in recipients if r.endswith("unicef.org")]
        external_rec = [r for r in recipients if not r.endswith("unicef.org")]
        if unicef_rec:
            context["pd_link"] = pd.get_frontend_object_url()
            send_notification_with_template(
                recipients=unicef_rec,
                template_name=template_name,
                context=context
            )
        if external_rec:
            context["pd_link"] = pd.get_frontend_object_url(to_unicef=False)
            send_notification_with_template(
                recipients=external_rec,
                template_name=template_name,
                context=context
            )


class PMPInterventionAcceptView(PMPInterventionActionView):
    def update(self, request, *args, **kwargs):
        pd = self.get_object()
        request.data.clear()
        if pd.status not in [Intervention.DRAFT]:
            raise ValidationError(_("Action is not allowed"))
        if self.is_partner_staff():
            if not self.is_partner_focal_point(pd):
                raise ValidationError(_("You need to be a focal point in order to perform this action"))
            if pd.partner_accepted:
                raise ValidationError(_("Partner has already accepted this PD."))
            if pd.unicef_court:
                raise ValidationError(_("You cannot perform this action while the PD "
                                      "is not available for partner to edit"))
            # When accepting on behalf of the partner since there is no further action, it will automatically
            # be sent to unicef
            request.data.update({"partner_accepted": True, "unicef_court": True})

            # if pd was created by unicef and sent to partner, submission date will be empty, so set it
            if not pd.submission_date:
                request.data.update({
                    "submission_date": timezone.now().strftime("%Y-%m-%d"),
                })

            recipients = [u.email for u in pd.unicef_focal_points.all()]
            template_name = 'partners/intervention/partner_accepted'
        else:
            if not pd.unicef_court:
                raise ValidationError(_("You cannot perform this action while the PD "
                                      "is not available for UNICEF to edit"))

            if pd.unicef_accepted:
                raise ValidationError(_("UNICEF has already accepted this PD."))

            if self.request.user not in pd.unicef_focal_points.all() and self.request.user != pd.budget_owner:
                raise ValidationError(_("Only focal points or budget owners can accept"))

            request.data.update({"unicef_accepted": True})
            recipients = [u.email for u in pd.partner_focal_points.all()]
            template_name = 'partners/intervention/unicef_accepted'

        response = super().update(request, *args, **kwargs)

        if response.status_code == 200:
            # send notification
            context = {
                "reference_number": pd.reference_number,
                "partner_name": str(pd.agreement.partner),
            }
            self.send_notification(
                pd,
                recipients=recipients,
                template_name=template_name,
                context=context
            )

        return response


class PMPInterventionAcceptOnBehalfOfPartner(PMPInterventionActionView):
    def update(self, request, *args, **kwargs):
        pd = self.get_object()
        request.data.clear()
        if pd.status not in [Intervention.DRAFT]:
            raise ValidationError(_("Action is not allowed"))

        if self.request.user not in pd.unicef_users_involved:
            raise ValidationError(_("Only focal points can accept"))

        if pd.partner_accepted:
            raise ValidationError(_("Partner has already accepted this PD."))

        request.data.update({
            "partner_accepted": True,
            "unicef_court": True,
            "accepted_on_behalf_of_partner": True,
        })

        if not pd.date_sent_to_partner:
            # if document accepted before it was sent to partner
            request.data.update({
                "date_sent_to_partner": timezone.now().date(),
            })

        if not pd.submission_date and 'submission_date' not in request.data:
            request.data.update({
                "submission_date": timezone.now().strftime("%Y-%m-%d"),
            })

        recipients = set(
            [u.email for u in pd.unicef_focal_points.all()] +
            [u.email for u in pd.partner_focal_points.all()]
        )
        recipients.discard(self.request.user.email)

        template_name = 'partners/intervention/unicef_accepted_behalf_of_partner'

        response = super().update(request, *args, **kwargs)

        if response.status_code == 200:
            # send notification
            context = {
                "reference_number": pd.reference_number,
                "partner_name": str(pd.agreement.partner),
            }
            self.send_notification(
                pd,
                recipients=list(recipients),
                template_name=template_name,
                context=context
            )

        return response


class PMPInterventionRejectReviewView(PMPInterventionActionView):
    @transaction.atomic
    def update(self, request, *args, **kwargs):
        if self.is_partner_staff():
            return HttpResponseForbidden()
        pd = self.get_object()
        if pd.status != Intervention.REVIEW:
            raise ValidationError(_("PD needs to be in Review state"))
        if not pd.review:
            raise ValidationError(_("PD review is missing"))
        if pd.review.overall_approver_id != request.user.pk:
            raise ValidationError(_("Only overall approver can reject review."))

        pd.review.overall_approval = False
        if not pd.review.review_date:
            pd.review.review_date = timezone.now().date()
        pd.review.save()

        request.data.clear()
        request.data.update({
            "status": Intervention.DRAFT,
            "unicef_accepted": False,
            "partner_accepted": False,
        })

        response = super().update(request, *args, **kwargs)
        template_name = 'partners/intervention/unicef_accepted_behalf_of_partner'
        if response.status_code == 200:
            recipients = set(
                [u.email for u in pd.unicef_focal_points.all()] +
                [pd.budget_owner.email]
            )
            # send notification
            context = {
                "reference_number": pd.reference_number,
                "partner_name": str(pd.agreement.partner),
                "review_actions": pd.review.actions_list,
                "pd_link": pd.get_frontend_object_url(),
            }
            self.send_notification(
                pd,
                recipients=list(recipients),
                template_name=template_name,
                context=context
            )

        return response


class PMPInterventionSendBackViewReview(PMPInterventionActionView):
    permission_classes = [IsAuthenticated, user_group_permission(PRC_SECRETARY)]

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        pd = self.get_object()
        if pd.status != Intervention.REVIEW:
            raise ValidationError(_("PD needs to be in Review state"))
        if not pd.review:
            raise ValidationError(_("PD review is missing"))
        if pd.review.overall_approval is not None:
            raise ValidationError(_("PD review already approved"))

        serializer = InterventionReviewSendBackSerializer(data=request.data, instance=pd.review)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        request.data.clear()
        request.data.update({
            "status": Intervention.DRAFT,
            "unicef_accepted": False,
            "partner_accepted": False,
        })

        response = super().update(request, *args, **kwargs)
        template_name = 'partners/intervention/prc_review_sent_back'
        if response.status_code == 200:
            recipients = set(
                [u.email for u in pd.unicef_focal_points.all()] +
                [pd.budget_owner.email]
            )
            # send notification
            context = {
                "reference_number": pd.reference_number,
                "pd_link": pd.get_frontend_object_url(suffix='review'),
            }
            send_notification_with_template(
                recipients=list(recipients),
                template_name=template_name,
                context=context
            )

        return response


class PMPInterventionReviewView(PMPInterventionActionView):
    @transaction.atomic
    def update(self, request, *args, **kwargs):
        if self.is_partner_staff():
            return HttpResponseForbidden()
        pd = self.get_object()
        if pd.status == Intervention.REVIEW:
            raise ValidationError(_("PD is already in Review status."))

        if pd.in_amendment:
            serializer = AmendedInterventionReviewActionSerializer(data=request.data)
        else:
            serializer = InterventionReviewActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        review = serializer.save(
            intervention=pd,
            submitted_by=request.user
        )

        request.data.clear()
        request.data.update({"status": Intervention.REVIEW})

        if review.review_type == InterventionReview.PRC and not pd.submission_date_prc:
            # save date when first prc review submitted
            request.data["submission_date_prc"] = timezone.now().date()

        response = super().update(request, *args, **kwargs)

        # difference should be updated only after everything is saved

        if pd.in_amendment:
            try:
                amendment = pd.amendment
                amendment.difference = amendment.get_difference()
                amendment.save()
            except InterventionAmendment.DoesNotExist:
                pass
            except MergeError as ex:
                raise ValidationError(
                    _('Merge Error: Amended field was already changed (%(field)s at %(instance)s). '
                      'This can be caused by parallel merged amendment or changed original intervention. '
                      'Amendment should be re-created.') % {'field': ex.field, 'instance': ex.instance}
                )

        if response.status_code == 200:
            # send notification
            recipients = set(
                u.email for u in pd.unicef_focal_points.all()
            )
            # context should be valid for both templates mentioned below
            context = {
                "reference_number": pd.reference_number,
                "partner_name": str(pd.agreement.partner),
                "budget_owner_name": f'{review.submitted_by.get_full_name()}'
            }

            # if review is not required (no-review), intervention will be transitioned to signature status
            if pd.status == Intervention.SIGNATURE:
                template_name = 'partners/intervention/unicef_signature'
            else:
                template_name = 'partners/intervention/unicef_sent_for_review'
                recipients = recipients.union(set(
                    get_user_model().objects.filter(
                        profile__country=connection.tenant,
                        realms__group=Group.objects.get(name=PRC_SECRETARY),
                    ).distinct().values_list('email', flat=True)
                ))

            self.send_notification(
                pd,
                recipients=recipients,
                template_name=template_name,
                context=context
            )

        return response


class PMPInterventionCancelView(PMPInterventionActionView):
    def update(self, request, *args, **kwargs):
        if self.is_partner_staff():
            return HttpResponseForbidden()
        pd = self.get_object()
        if pd.status == Intervention.CANCELLED:
            raise ValidationError(_("PD has already been cancelled."))

        if self.request.user not in pd.unicef_focal_points.all() and self.request.user != pd.budget_owner:
            raise ValidationError(_("Only focal points or budget owners can cancel"))

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
            }
            self.send_notification(
                pd,
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
            raise ValidationError(_("PD has already been terminated."))

        if self.request.user not in pd.unicef_focal_points.all() and self.request.user != pd.budget_owner:
            raise ValidationError(_("Only focal points or budget owners can terminate"))

        # override status as terminated
        request.data.update({"status": Intervention.TERMINATED})
        response = super().update(request, *args, **kwargs)

        if response.status_code == 200:
            # send notification
            recipients = set([
                u.email for u in pd.unicef_users_involved
            ] + [
                u.email for u in pd.unicef_focal_points.all()
            ])
            context = {
                "reference_number": pd.reference_number,
                "partner_name": str(pd.agreement.partner),
            }
            self.send_notification(
                pd,
                recipients=recipients,
                template_name='partners/intervention/unicef_terminated',
                context=context
            )

        return response


class PMPInterventionSuspendView(PMPInterventionActionView):
    def update(self, request, *args, **kwargs):
        if self.is_partner_staff():
            return HttpResponseForbidden()
        pd = self.get_object()
        if pd.status == Intervention.SUSPENDED:
            raise ValidationError(_("PD has already been suspended."))

        if self.request.user not in pd.unicef_focal_points.all() and self.request.user != pd.budget_owner:
            raise ValidationError(_("Only focal points or budget owners can suspend"))

        # override status as suspended
        request.data.update({"status": Intervention.SUSPENDED})
        response = super().update(request, *args, **kwargs)

        if response.status_code == 200:
            # send notification
            recipients = [
                u.email for u in pd.unicef_users_involved
            ] + [
                u.email for u in pd.unicef_focal_points.all()
            ]
            context = {
                "reference_number": pd.reference_number,
                "partner_name": str(pd.agreement.partner)
            }
            self.send_notification(
                pd,
                recipients=recipients,
                template_name='partners/intervention/unicef_suspended',
                context=context
            )

        return response


class PMPInterventionUnsuspendView(PMPInterventionActionView):
    def update(self, request, *args, **kwargs):
        if self.is_partner_staff():
            return HttpResponseForbidden()
        pd = self.get_object()
        if pd.status != Intervention.SUSPENDED:
            raise ValidationError(_("PD is not suspended."))

        if self.request.user not in pd.unicef_focal_points.all() and self.request.user != pd.budget_owner:
            raise ValidationError(_("Only focal points or budget owners can unsuspend"))

        # override status as active
        request.data.update({"status": Intervention.ACTIVE})
        response = super().update(request, *args, **kwargs)

        if response.status_code == 200:
            # send notification
            recipients = [
                u.email for u in pd.unicef_users_involved
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
            self.send_notification(
                pd,
                recipients=recipients,
                template_name='partners/intervention/unicef_unsuspended',
                context=context
            )

        return response


class PMPInterventionSignatureView(PMPInterventionActionView):
    def update(self, request, *args, **kwargs):
        if self.is_partner_staff():
            return HttpResponseForbidden()
        pd = self.get_object()
        if pd.status == Intervention.SIGNATURE:
            raise ValidationError(_("PD is already in Signature status."))
        if not pd.review:
            raise ValidationError(_("PD review is missing"))
        if pd.review.overall_approver_id != request.user.pk:
            raise ValidationError(_("Only overall approver can accept review."))

        pd.review.overall_approval = True
        if not pd.review.review_date:
            pd.review.review_date = timezone.now().date()
        pd.review.save()

        request.data.clear()
        request.data.update({"status": Intervention.SIGNATURE})
        if pd.review.review_type == InterventionReview.PRC:
            request.data["review_date_prc"] = timezone.now().date()

        response = super().update(request, *args, **kwargs)

        if response.status_code == 200:
            # send notification
            recipients = set([
                u.email for u in pd.unicef_users_involved
            ])
            context = {
                "reference_number": pd.reference_number,
                "partner_name": str(pd.agreement.partner)
            }
            self.send_notification(
                pd,
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
            raise ValidationError(_("PD is already unlocked."))

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
                "partner_name": str(pd.agreement.partner)
            }
            self.send_notification(
                pd,
                recipients=recipients,
                template_name=template_name,
                context=context
            )

        return response


class PMPInterventionSendToPartnerView(PMPInterventionActionView):
    def update(self, request, *args, **kwargs):
        pd = self.get_object()
        if not pd.unicef_court:
            raise ValidationError(_("PD is currently with Partner"))

        if self.request.user not in pd.unicef_focal_points.all() and self.request.user != pd.budget_owner:
            raise ValidationError(_("Only focal points or budget owners can send to partner"))

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
                "partner_name": str(pd.agreement.partner)
            }
            self.send_notification(
                pd,
                recipients=recipients,
                template_name='partners/intervention/send_to_partner',
                context=context
            )

        return response


class PMPInterventionSendToUNICEFView(PMPInterventionActionView):
    def update(self, request, *args, **kwargs):
        pd = self.get_object()
        if pd.unicef_court:
            raise ValidationError(_("PD is currently with UNICEF"))

        if not self.is_partner_focal_point(pd):
            raise ValidationError(_("Only partner focal points can send to UNICEF"))

        request.data.clear()
        request.data.update({"unicef_court": True})
        if not pd.submission_date:
            request.data.update({
                "submission_date": timezone.now().strftime("%Y-%m-%d"),
            })

        response = super().update(request, *args, **kwargs)

        if response.status_code == 200:
            # notify unicef
            recipients = [u.email for u in pd.unicef_focal_points.all()]
            context = {
                "reference_number": pd.reference_number,
                "partner_name": str(pd.agreement.partner)
            }
            self.send_notification(
                pd,
                recipients=recipients,
                template_name='partners/intervention/send_to_unicef',
                context=context
            )

        return response


class PMPAmendedInterventionMerge(InterventionDetailAPIView):
    permission_classes = (
        user_group_permission(PARTNERSHIP_MANAGER_GROUP) | IsInterventionBudgetOwnerPermission | UserIsUnicefFocalPoint,
    )

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        pd = self.get_object()
        if not pd.in_amendment:
            raise ValidationError(_('Only amended interventions can be merged'))
        if not pd.status == Intervention.SIGNED:
            raise ValidationError(_('Amendment cannot be merged yet'))
        try:
            amendment = pd.amendment
        except InterventionAmendment.DoesNotExist:
            raise ValidationError(_('Amendment does not exist for this pd'))

        try:
            amendment.merge_amendment()
        except MergeError as ex:
            raise ValidationError(
                _('Merge Error: Amended field was already changed (%(field)s at %(instance)s). '
                  'This can be caused by parallel merged amendment or changed original intervention. '
                  'Amendment should be re-created.') % {'field': ex.field, 'instance': ex.instance}
            )

        transaction.on_commit(lambda: send_pd_to_vision.delay(connection.tenant.name, pd.pk))

        return Response(
            InterventionDetailSerializer(
                amendment.intervention,
                context=self.get_serializer_context(),
            ).data
        )
