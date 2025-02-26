from django.conf import settings
from django.utils.translation import gettext as _

from easy_pdf.rendering import render_to_pdf_response
from rest_framework import status
from rest_framework.generics import (
    GenericAPIView,
    get_object_or_404,
    ListAPIView,
    RetrieveAPIView,
    RetrieveUpdateAPIView,
    UpdateAPIView,
)
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from etools.applications.field_monitoring.permissions import IsEditAction, IsReadAction
from etools.applications.governments.models import GDD, GDDPRCOfficerReview, GDDReview, GDDReviewNotification
from etools.applications.governments.permissions import (
    gdd_field_has_view_permission,
    gdd_field_is_editable_permission,
    UserBelongsToObjectPermission,
    UserIsStaffPermission,
)
from etools.applications.governments.serializers.helpers import GDDPRCOfficerReviewSerializer, GDDReviewSerializer
from etools.applications.governments.views.gdd import DetailedGDDResponseMixin, GDDBaseViewMixin
from etools.libraries.djangolib.utils import get_current_site


class GDDReviewMixin(DetailedGDDResponseMixin, GDDBaseViewMixin):
    queryset = GDDReview.objects.all()
    permission_classes = [
        IsAuthenticated,
        IsReadAction | (IsEditAction & gdd_field_is_editable_permission('reviews'))
    ]
    serializer_class = GDDReviewSerializer

    def get_root_object(self):
        return GDD.objects.get(pk=self.kwargs["gdd_pk"])

    def get_gdd(self):
        return self.get_root_object()

    def get_queryset(self):
        qs = super().get_queryset().filter(
            gdd__pk=self.kwargs["gdd_pk"],
        )
        if self.is_partner_staff():
            return qs.none()
        return qs

    def get_serializer(self, *args, **kwargs):
        if "data" in kwargs:
            kwargs["data"]["gdd"] = self.get_root_object().pk
        return super().get_serializer(*args, **kwargs)


class GDDReviewView(GDDReviewMixin, ListAPIView):
    lookup_url_kwarg = "gdd_pk"
    lookup_field = "gdd_id"


class GDDReviewDetailView(GDDReviewMixin, RetrieveUpdateAPIView):
    pass


class GDDReviewDetailPDFView(GDDReviewMixin, RetrieveAPIView):
    permission_classes = [
        IsAuthenticated,
        IsReadAction & gdd_field_has_view_permission('reviews')
    ]

    def get(self, request, *args, **kwargs):
        gdd = self.get_root_object()
        review = get_object_or_404(self.get_queryset(), pk=self.kwargs.get('review_pk'))

        font_path = settings.PACKAGE_ROOT + '/assets/fonts/'

        data = {
            "domain": 'https://{}'.format(get_current_site().domain),
            "gdd": gdd,
            "review": review,
            "prc_reviews": review.prc_reviews.filter(review_date__isnull=False),
            "font_path": font_path,
        }

        return render_to_pdf_response(request, "gdd/prc_review_pdf.html", data, filename=f'PRC_Review_{str(gdd)}.pdf')


class GDDOfficerReviewBaseView(DetailedGDDResponseMixin, GDDBaseViewMixin):
    queryset = GDDPRCOfficerReview.objects.prefetch_related('user').all()
    serializer_class = GDDPRCOfficerReviewSerializer

    def get_root_object(self):
        return GDD.objects.get(pk=self.kwargs['gdd_pk'])

    def get_gdd(self):
        return self.get_root_object()

    def get_queryset(self):
        qs = super().get_queryset().filter(
            overall_review_id=self.kwargs['review_pk'],
            overall_review__gdd_id=self.kwargs['gdd_pk'],
        )
        if self.is_partner_staff():
            return qs.none()
        return qs


class GDDOfficerReviewListView(GDDOfficerReviewBaseView, ListAPIView):
    permission_classes = [IsAuthenticated, UserIsStaffPermission]


class GDDOfficerReviewDetailView(GDDOfficerReviewBaseView, UpdateAPIView):
    permission_classes = [
        IsAuthenticated,
        UserIsStaffPermission,
        gdd_field_is_editable_permission('reviews'),
        UserBelongsToObjectPermission,
    ]
    lookup_field = 'user_id'
    lookup_url_kwarg = 'user_pk'


class GDDReviewNotifyView(GDDReviewMixin, GenericAPIView):
    def post(self, request, *args, **kwargs):
        review = self.get_object()
        if not review.meeting_date:
            return Response([_('Meeting date is not available.')], status=status.HTTP_400_BAD_REQUEST)

        GDDReviewNotification.notify_officers_for_review(review)
        return Response({})


class GDDReviewNotifyAuthorizedOfficerView(GDDReviewMixin, GenericAPIView):
    def post(self, request, *args, **kwargs):
        review = self.get_object()

        sent = GDDReviewNotification.notify_authorized_officer_for_review(review)
        if not sent:
            return Response({"already_sent_today": True}, status=status.HTTP_400_BAD_REQUEST)

        return Response({"success": True})
