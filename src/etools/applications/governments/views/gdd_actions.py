from django.contrib.auth import get_user_model
from django.db import connection, transaction
from django.db.models import OuterRef, Subquery
from django.http import HttpResponseForbidden
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext as _

from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from etools.applications.environment.helpers import tenant_switch_is_active
from etools.applications.environment.notifications import send_notification_with_template
from etools.applications.governments.models import GDD, GDDAmendment, GDDReview
from etools.applications.governments.permissions import (
    IsGDDBudgetOwnerPermission,
    PARTNERSHIP_MANAGER_GROUP,
    PRC_SECRETARY,
    user_group_permission,
    UserIsReviewAuthorizedOfficer,
    UserIsReviewOverallApprover,
    UserIsUnicefFocalPoint,
)
from etools.applications.governments.serializers.gdd import GDDDetailSerializer
from etools.applications.governments.serializers.gdd_actions import (
    AmendedGDDReviewActionSerializer,
    GDDReviewActionSerializer,
    GDDReviewSendBackSerializer,
)
from etools.applications.governments.tasks import send_gdd_to_vision
from etools.applications.governments.views.gdd import GDDRetrieveUpdateView
from etools.applications.partners.amendment_utils import MergeError
from etools.applications.users.models import Realm
from etools.applications.utils.helpers import lock_request


class GDDActionView(GDDRetrieveUpdateView):
    def update(self, request, *args, **kwargs):
        response = super().update(request, *args, **kwargs)
        # need to overwrite successful response, so we get v3 serializer
        if response.status_code == 200:
            response = Response(
                GDDDetailSerializer(
                    self.instance,
                    context=self.get_serializer_context(),
                ).data,
            )
        return response

    def is_partner_focal_point(self, gdd):
        return self.request.user in gdd.partner_focal_points.all()

    def send_notification(self, gdd, recipients, template_name, context):
        unicef_rec = [r for r in recipients if r.endswith("unicef.org")]
        external_rec = [r for r in recipients if not r.endswith("unicef.org")]
        if unicef_rec:
            context["gdd_link"] = gdd.get_frontend_object_url()
            send_notification_with_template(
                recipients=unicef_rec,
                template_name=template_name,
                context=context
            )
        if external_rec:
            context["gdd_link"] = gdd.get_frontend_object_url(to_unicef=False)
            send_notification_with_template(
                recipients=external_rec,
                template_name=template_name,
                context=context
            )


class GDDAcceptView(GDDActionView):
    def update(self, request, *args, **kwargs):
        gdd = self.get_object()
        request.data.clear()
        if gdd.status not in [GDD.DRAFT]:
            raise ValidationError(_("Action is not allowed"))
        if self.is_partner_staff():
            if not self.is_partner_focal_point(gdd):
                raise ValidationError(_("You need to be a focal point in order to perform this action"))
            if gdd.partner_accepted:
                raise ValidationError(_("Partner has already accepted this GDD."))
            if gdd.unicef_court:
                raise ValidationError(_("You cannot perform this action while the GDD "
                                      "is not available for partner to edit"))
            # When accepting on behalf of the partner since there is no further action, it will automatically
            # be sent to unicef
            request.data.update({"partner_accepted": True, "unicef_court": True})

            # if gdd was created by unicef and sent to partner, submission date will be empty, so set it
            if not gdd.submission_date:
                request.data.update({
                    "submission_date": timezone.now().strftime("%Y-%m-%d"),
                })

            recipients = [u.email for u in gdd.unicef_focal_points.all()]
            template_name = 'governments/gdd/partner_accepted'
        else:
            if not gdd.unicef_court:
                raise ValidationError(_("You cannot perform this action while the GDD "
                                      "is not available for UNICEF to edit"))

            if gdd.unicef_accepted:
                raise ValidationError(_("UNICEF has already accepted this GDD."))

            if self.request.user not in gdd.unicef_focal_points.all() and self.request.user != gdd.budget_owner:
                raise ValidationError(_("Only focal points or budget owners can accept"))

            request.data.update({"unicef_accepted": True})
            recipients = [u.email for u in gdd.partner_focal_points.all()]
            template_name = 'governments/gdd/unicef_accepted'

        response = super().update(request, *args, **kwargs)

        if response.status_code == 200:
            # send notification
            context = {
                "reference_number": gdd.reference_number,
                "partner_name": str(gdd.partner),
            }
            self.send_notification(
                gdd,
                recipients=recipients,
                template_name=template_name,
                context=context
            )

        return response


class GDDAcceptOnBehalfOfPartner(GDDActionView):
    def update(self, request, *args, **kwargs):
        gdd = self.get_object()
        request.data.clear()
        if gdd.status not in [GDD.DRAFT]:
            raise ValidationError(_("Action is not allowed"))

        if self.request.user not in gdd.unicef_users_involved:
            raise ValidationError(_("Only focal points can accept"))

        if gdd.partner_accepted:
            raise ValidationError(_("Partner has already accepted this GDD."))

        request.data.update({
            "partner_accepted": True,
            "unicef_court": True,
            "accepted_on_behalf_of_partner": True,
        })

        if not gdd.date_sent_to_partner:
            # if document accepted before it was sent to partner
            request.data.update({
                "date_sent_to_partner": timezone.now().date(),
            })

        if not gdd.submission_date and 'submission_date' not in request.data:
            request.data.update({
                "submission_date": timezone.now().strftime("%Y-%m-%d"),
            })

        recipients = set(
            [u.email for u in gdd.unicef_focal_points.all()] +
            [u.email for u in gdd.partner_focal_points.all()]
        )
        recipients.discard(self.request.user.email)

        template_name = 'governments/gdd/unicef_accepted_behalf_of_partner'

        response = super().update(request, *args, **kwargs)

        if response.status_code == 200:
            # send notification
            context = {
                "reference_number": gdd.reference_number,
                "partner_name": str(gdd.partner),
            }
            self.send_notification(
                gdd,
                recipients=list(recipients),
                template_name=template_name,
                context=context
            )

        return response


class GDDRejectReviewView(GDDActionView):
    @transaction.atomic
    def update(self, request, *args, **kwargs):
        if self.is_partner_staff():
            return HttpResponseForbidden()
        gdd = self.get_object()
        if gdd.status != GDD.REVIEW:
            raise ValidationError(_("GDD needs to be in Review state"))
        if not gdd.review:
            raise ValidationError(_("GDD review is missing"))
        if gdd.review.overall_approver_id != request.user.pk:
            raise ValidationError(_("Only overall approver can reject review."))

        gdd.review.overall_approval = False
        if not gdd.review.review_date:
            gdd.review.review_date = timezone.now().date()
        gdd.review.save()

        request.data.clear()
        request.data.update({
            "status": GDD.DRAFT,
            "unicef_accepted": False,
            "partner_accepted": False,
        })

        response = super().update(request, *args, **kwargs)
        template_name = 'governments/gdd/unicef_accepted_behalf_of_partner'
        if response.status_code == 200:
            recipients = set(
                [u.email for u in gdd.unicef_focal_points.all()] +
                [gdd.budget_owner.email]
            )
            # send notification
            context = {
                "reference_number": gdd.reference_number,
                "partner_name": str(gdd.partner),
                "review_actions": gdd.review.actions_list,
                "pd_link": gdd.get_frontend_object_url(),
            }
            self.send_notification(
                gdd,
                recipients=list(recipients),
                template_name=template_name,
                context=context
            )

        return response


class GDDSendBackViewReview(GDDActionView):
    permission_classes = [
        IsAuthenticated,
        user_group_permission(PRC_SECRETARY) | UserIsReviewOverallApprover | UserIsReviewAuthorizedOfficer,
    ]

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        gdd = self.get_object()
        if gdd.status != GDD.REVIEW:
            raise ValidationError(_("GDD needs to be in Review state"))
        if not gdd.review:
            raise ValidationError(_("GDD review is missing"))
        if gdd.review.overall_approval is not None:
            raise ValidationError(_("GDD review already approved"))

        serializer = GDDReviewSendBackSerializer(data=request.data, instance=gdd.review)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        request.data.clear()
        request.data.update({
            "status": GDD.DRAFT,
            "unicef_accepted": False,
            "partner_accepted": False,
        })

        response = super().update(request, *args, **kwargs)
        template_name = 'governments/gdd/prc_review_sent_back'
        if response.status_code == 200:
            recipients = set(
                [u.email for u in gdd.unicef_focal_points.all()] +
                [gdd.budget_owner.email]
            )
            # send notification
            context = {
                "reference_number": gdd.reference_number,
                "pd_link": gdd.get_frontend_object_url(suffix='review'),
            }
            send_notification_with_template(
                recipients=list(recipients),
                template_name=template_name,
                context=context
            )

        return response


class GDDReviewView(GDDActionView):
    @transaction.atomic
    def update(self, request, *args, **kwargs):
        if self.is_partner_staff():
            return HttpResponseForbidden()
        gdd = self.get_object()
        if gdd.status == GDD.REVIEW:
            raise ValidationError(_("GDD is already in Review status."))

        if gdd.in_amendment:
            serializer = AmendedGDDReviewActionSerializer(data=request.data)
        else:
            serializer = GDDReviewActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        review = serializer.save(
            gdd=gdd,
            submitted_by=request.user
        )

        request.data.clear()
        request.data.update({"status": GDD.REVIEW})

        if review.review_type in [GDDReview.PRC, GDDReview.NPRC] and not gdd.submission_date_prc:
            # save date when first prc review submitted
            request.data["submission_date_prc"] = timezone.now().date()

        response = super().update(request, *args, **kwargs)

        # difference should be updated only after everything is saved

        if gdd.in_amendment:
            try:
                amendment = gdd.amendment
                amendment.difference = amendment.get_difference()
                amendment.save()
            except GDDAmendment.DoesNotExist:
                pass
            except MergeError as ex:
                raise ValidationError(
                    _('Merge Error: Amended field was already changed (%(field)s at %(instance)s). '
                      'This can be caused by parallel merged amendment or changed original gdd. '
                      'Amendment should be re-created.') % {'field': ex.field, 'instance': ex.instance}
                )

        if response.status_code == 200:
            # send notification
            recipients = set(
                u.email for u in gdd.unicef_focal_points.all()
            )
            # context should be valid for both templates mentioned below
            context = {
                "reference_number": gdd.reference_number,
                "partner_name": str(gdd.partner),
                "budget_owner_name": f'{review.submitted_by.get_full_name()}'
            }

            # if review is not required (no-review), gdd will be transitioned to pending approval status
            if gdd.status == GDD.PENDING_APPROVAL:
                template_name = 'governments/gdd/unicef_pending_approval'
            else:
                template_name = 'governments/gdd/unicef_sent_for_review'
                active_prc_realm_subquery = Realm.objects.filter(
                    country=connection.tenant,
                    group__name=PRC_SECRETARY,
                    is_active=True,
                    pk=OuterRef('realms')
                ).values('pk')
                recipients = recipients.union(set(
                    get_user_model().objects.filter(profile__country=connection.tenant,
                                                    realms__in=Subquery(active_prc_realm_subquery),
                                                    ).distinct().values_list('email', flat=True)
                ))

            self.send_notification(
                gdd,
                recipients=recipients,
                template_name=template_name,
                context=context
            )

        return response


class GDDCancelView(GDDActionView):
    def update(self, request, *args, **kwargs):
        if self.is_partner_staff():
            return HttpResponseForbidden()
        gdd = self.get_object()
        if gdd.status == GDD.CANCELLED:
            raise ValidationError(_("GDD has already been cancelled."))

        if not request.user.groups.filter(name=PRC_SECRETARY).exists():
            raise ValidationError(_("Only PRC Secretary can cancel"))

        request.data.update({"status": GDD.CANCELLED})

        response = super().update(request, *args, **kwargs)

        if response.status_code == 200:
            # send notification
            recipients = [
                u.email for u in gdd.partner_focal_points.all()
            ] + [
                u.email for u in gdd.unicef_focal_points.all()
            ]
            context = {
                "reference_number": gdd.reference_number,
                "partner_name": str(gdd.partner),
            }
            self.send_notification(
                gdd,
                recipients=recipients,
                template_name='governments/gdd/unicef_cancelled',
                context=context
            )

        return response


class GDDTerminateView(GDDActionView):
    def update(self, request, *args, **kwargs):
        if self.is_partner_staff():
            return HttpResponseForbidden()
        gdd = self.get_object()
        if gdd.status == GDD.TERMINATED:
            raise ValidationError(_("GDD has already been terminated."))

        if self.request.user not in gdd.unicef_focal_points.all() and self.request.user != gdd.budget_owner:
            raise ValidationError(_("Only focal points or budget owners can terminate"))

        # override status as terminated
        request.data.update({"status": GDD.TERMINATED})
        response = super().update(request, *args, **kwargs)

        if response.status_code == 200:
            # send notification
            recipients = set([
                u.email for u in gdd.unicef_users_involved
            ] + [
                u.email for u in gdd.unicef_focal_points.all()
            ])
            context = {
                "reference_number": gdd.reference_number,
                "partner_name": str(gdd.partner),
            }
            self.send_notification(
                gdd,
                recipients=recipients,
                template_name='governments/gdd/unicef_terminated',
                context=context
            )

        return response


class GDDSuspendView(GDDActionView):
    def update(self, request, *args, **kwargs):
        if self.is_partner_staff():
            return HttpResponseForbidden()
        gdd = self.get_object()
        if gdd.status == GDD.SUSPENDED:
            raise ValidationError(_("GDD has already been suspended."))

        if self.request.user not in gdd.unicef_focal_points.all() and self.request.user != gdd.budget_owner:
            raise ValidationError(_("Only focal points or budget owners can suspend"))

        # override status as suspended
        request.data.update({"status": GDD.SUSPENDED})
        response = super().update(request, *args, **kwargs)

        if response.status_code == 200:
            # send notification
            recipients = [
                u.email for u in gdd.unicef_users_involved
            ] + [
                u.email for u in gdd.unicef_focal_points.all()
            ]
            context = {
                "reference_number": gdd.reference_number,
                "partner_name": str(gdd.partner)
            }
            self.send_notification(
                gdd,
                recipients=recipients,
                template_name='governments/gdd/unicef_suspended',
                context=context
            )

        return response


class GDDUnsuspendView(GDDActionView):
    def update(self, request, *args, **kwargs):
        if self.is_partner_staff():
            return HttpResponseForbidden()
        gdd = self.get_object()
        if gdd.status != GDD.SUSPENDED:
            raise ValidationError(_("GDD is not suspended."))

        if self.request.user not in gdd.unicef_focal_points.all() and self.request.user != gdd.budget_owner:
            raise ValidationError(_("Only focal points or budget owners can unsuspend"))

        # override status as active
        request.data.update({"status": GDD.ACTIVE})
        response = super().update(request, *args, **kwargs)

        if response.status_code == 200:
            # send notification
            recipients = [
                u.email for u in gdd.unicef_users_involved
            ] + [
                u.email for u in gdd.unicef_focal_points.all()
            ]
            context = {
                "reference_number": gdd.reference_number,
                "partner_name": str(gdd.partner),
                "pd_link": "to be implemented",
            }
            self.send_notification(
                gdd,
                recipients=recipients,
                template_name='governments/gdd/unicef_unsuspended',
                context=context
            )

        return response


class GDDSignatureView(GDDActionView):
    def update(self, request, *args, **kwargs):
        if self.is_partner_staff():
            return HttpResponseForbidden()
        gdd = self.get_object()
        if gdd.status == GDD.PENDING_APPROVAL:
            raise ValidationError(_("GDD is already in Pending Approval status."))
        if not gdd.review:
            raise ValidationError(_("GDD review is missing"))
        if gdd.review.authorized_officer_id != request.user.pk:
            raise ValidationError(_("Only authorized officer can accept review."))

        gdd.review.overall_approval = True
        if not gdd.review.review_date:
            gdd.review.review_date = timezone.now().date()
        gdd.review.save()

        request.data.clear()
        request.data.update({"status": GDD.PENDING_APPROVAL})
        if gdd.review.review_type in [GDDReview.PRC, GDDReview.NPRC]:
            request.data["review_date_prc"] = timezone.now().date()

        response = super().update(request, *args, **kwargs)

        if response.status_code == 200:
            # send notification
            recipients = set([
                u.email for u in gdd.unicef_users_involved
            ])
            context = {
                "reference_number": gdd.reference_number,
                "partner_name": str(gdd.partner)
            }
            self.send_notification(
                gdd,
                recipients=recipients,
                template_name='governments/gdd/unicef_pending_approval',
                context=context
            )

        return response


class GDDUnlockView(GDDActionView):
    def update(self, request, *args, **kwargs):
        gdd = self.get_object()
        request.data.clear()
        if not gdd.locked:
            raise ValidationError(_("GDD is already unlocked."))

        if self.is_partner_staff():
            recipients = [u.email for u in gdd.unicef_focal_points.all()]
            template_name = 'governments/gdd/partner_unlocked'
        else:
            recipients = [u.email for u in gdd.partner_focal_points.all()]
            template_name = 'governments/gdd/unicef_unlocked'

        request.data.update({"partner_accepted": False, "unicef_accepted": False})
        response = super().update(request, *args, **kwargs)

        if response.status_code == 200:
            # send notification
            context = {
                "reference_number": gdd.reference_number,
                "partner_name": str(gdd.partner)
            }
            self.send_notification(
                gdd,
                recipients=recipients,
                template_name=template_name,
                context=context
            )

        return response


class GDDSendToPartnerView(GDDActionView):
    def update(self, request, *args, **kwargs):
        gdd = self.get_object()
        if not gdd.unicef_court:
            raise ValidationError(_("GDD is currently with Partner"))

        if self.request.user not in gdd.unicef_focal_points.all() and self.request.user != gdd.budget_owner:
            raise ValidationError(_("Only focal points or budget owners can send to partner"))

        request.data.clear()
        request.data.update({"unicef_court": False})
        if not gdd.date_sent_to_partner:
            request.data.update({
                "date_sent_to_partner": timezone.now().strftime("%Y-%m-%d"),
            })

        response = super().update(request, *args, **kwargs)

        if response.status_code == 200:
            # notify partner
            recipients = [u.email for u in gdd.partner_focal_points.all()]
            context = {
                "reference_number": gdd.reference_number,
                "partner_name": str(gdd.partner)
            }
            self.send_notification(
                gdd,
                recipients=recipients,
                template_name='governments/gdd/send_to_partner',
                context=context
            )

        return response


class GDDSendToUNICEFView(GDDActionView):
    def update(self, request, *args, **kwargs):
        gdd = self.get_object()
        if gdd.unicef_court:
            raise ValidationError(_("GDD is currently with UNICEF"))

        if not self.is_partner_focal_point(gdd):
            raise ValidationError(_("Only partner focal points can send to UNICEF"))

        request.data.clear()
        request.data.update({"unicef_court": True})
        if not gdd.submission_date:
            request.data.update({
                "submission_date": timezone.now().strftime("%Y-%m-%d"),
            })

        response = super().update(request, *args, **kwargs)

        if response.status_code == 200:
            # notify unicef
            recipients = [u.email for u in gdd.unicef_focal_points.all()]
            context = {
                "reference_number": gdd.reference_number,
                "partner_name": str(gdd.partner)
            }
            self.send_notification(
                gdd,
                recipients=recipients,
                template_name='governments/gdd/send_to_unicef',
                context=context
            )

        return response


class PMPAmendedGDDMerge(GDDRetrieveUpdateView):
    permission_classes = (
        user_group_permission(PARTNERSHIP_MANAGER_GROUP) | IsGDDBudgetOwnerPermission | UserIsUnicefFocalPoint,
    )

    @transaction.atomic
    @lock_request
    def update(self, request, *args, **kwargs):
        gdd = self.get_object()
        if not gdd.in_amendment:
            raise ValidationError(_('Only amended gdds can be merged'))
        if not gdd.status == GDD.APPROVED:
            raise ValidationError(_('Amendment cannot be merged yet'))
        try:
            amendment = gdd.amendment
        except GDDAmendment.DoesNotExist:
            raise ValidationError(_('Amendment does not exist for thisgdd'))

        try:
            amendment.merge_amendment()
        except MergeError as ex:
            raise ValidationError(
                _('Merge Error: Amended field was already changed (%(field)s at %(instance)s). '
                  'This can be caused by parallel merged amendment or changed original gdd. '
                  'Amendment should be re-created.') % {'field': ex.field, 'instance': ex.instance}
            )

        if not tenant_switch_is_active('disable_pd_vision_sync'):
            transaction.on_commit(lambda: send_gdd_to_vision.delay(connection.tenant.name, amendment.gdd.pk))

        return Response(
            GDDDetailSerializer(
                amendment.gdd,
                context=self.get_serializer_context(),
            ).data
        )
