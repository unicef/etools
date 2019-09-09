from django.contrib.contenttypes.models import ContentType
from django.shortcuts import get_object_or_404
from django.utils.translation import ugettext_lazy as _

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from unicef_attachments.models import Attachment
from unicef_restlib.pagination import DynamicPageNumberPagination
from unicef_restlib.views import NestedViewSetMixin, QueryStringFilterMixin, SafeTenantViewSetMixin

from etools.applications.psea.models import Answer, Assessment, Assessor, Indicator
from etools.applications.psea.permissions import AssessmentPermissions
from etools.applications.psea.serializers import (
    AnswerAttachmentSerializer,
    AnswerSerializer,
    AssessmentSerializer,
    AssessmentStatusSerializer,
    AssessorSerializer,
    IndicatorSerializer,
)


class AssessmentViewSet(
        SafeTenantViewSetMixin,
        QueryStringFilterMixin,
        mixins.CreateModelMixin,
        mixins.ListModelMixin,
        mixins.UpdateModelMixin,
        mixins.RetrieveModelMixin,
        viewsets.GenericViewSet,
):
    pagination_class = DynamicPageNumberPagination
    permission_classes = [IsAuthenticated, ]

    queryset = Assessment.objects.all()
    serializer_class = AssessmentSerializer

    filter_backends = (SearchFilter, DjangoFilterBackend, OrderingFilter)
    filters = (
        ('q', [
            'reference_number__icontains',
            'assessor__auditor_firm__name__icontains',
            'assessor__user__first_name__icontains',
            'assessor__user__last_name__icontains',
        ]),
        ('partner', 'partner_id__in'),
        ('status', 'status__in'),
        ('unicef_focal_point', 'focal_points__pk__in'),
        ('assessment_date', 'assessment_date'),
        ('assessor_staff', 'assessor__user__pk__in'),
        ('assessor_external', 'assessor__user__pk__in'),
        ('assessor_firm', 'assessor__auditor_firm__pk__in'),
    )
    # TODO add sort
    export_filename = 'Assessment'

    def parse_sort_params(self):
        MAP_SORT = {
            "reference_number": "reference_number",
            "assessment_date": "assessment_date",
            "partner_name": "partner__name",
        }
        sort_param = self.request.GET.get("sort")
        ordering = []
        if sort_param:
            sort_options = sort_param.split("|")
            for sort in sort_options:
                field, asc_desc = sort.split(".", 2)
                if field in MAP_SORT:
                    ordering.append(
                        "{}{}".format(
                            "-" if asc_desc == "desc" else "",
                            MAP_SORT[field],
                        )
                    )
        return ordering

    def get_queryset(self):
        qs = super().get_queryset()
        if "sort" in self.request.GET:
            qs = qs.order_by(*self.parse_sort_params())
        return qs

    def _set_status(self, request, assessment_status):
        assessment = self.get_object()
        data = request.data
        if "status" not in data:
            data["status"] = assessment_status
        serializer = AssessmentStatusSerializer(
            instance=assessment,
            data=data,
            context={"request": request},
        )
        if serializer.is_valid():
            assessment.status = assessment_status
            assessment.save()
            comment = serializer.validated_data.get("comment")
            if comment is not None:
                history = assessment.status_history.first()
                history.comment = serializer.validated_data.get("comment")
                history.save()
            return Response({"status": assessment_status})
        else:
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST,
            )

    @action(detail=True, methods=["patch"])
    def assigned(self, request, pk=None):
        return self._set_status(request, Assessment.STATUS_ASSIGNED)

    @action(detail=True, methods=["patch"])
    def progress(self, request, pk=None):
        return self._set_status(request, Assessment.STATUS_IN_PROGRESS)

    @action(detail=True, methods=["patch"])
    def submitted(self, request, pk=None):
        return self._set_status(request, Assessment.STATUS_SUBMITTED)

    @action(detail=True, methods=["patch"])
    def final(self, request, pk=None):
        return self._set_status(request, Assessment.STATUS_FINAL)

    @action(detail=True, methods=["patch"])
    def cancelled(self, request, pk=None):
        return self._set_status(request, Assessment.STATUS_CANCELLED)

    @action(detail=True, methods=["patch"])
    def rejected(self, request, pk=None):
        return self._set_status(request, Assessment.STATUS_IN_PROGRESS)


class AssessorViewSet(
        SafeTenantViewSetMixin,
        mixins.CreateModelMixin,
        mixins.UpdateModelMixin,
        mixins.ListModelMixin,
        viewsets.GenericViewSet,
):
    permission_classes = [IsAuthenticated, ]
    queryset = Assessor.objects.all()
    serializer_class = AssessorSerializer

    def get_queryset(self):
        return self.queryset.filter(assessment=self.kwargs.get("nested_1_pk"))

    def check_assessment_permissions(self):
        try:
            assessment = Assessment.objects.get(id=self.kwargs.get("nested_1_pk"))
        except Assessment.DoesNotExist:
            raise ValidationError("Assessment object id incorrect")
        p = AssessmentPermissions(
            user=self.request.user,
            instance=assessment,
            permission_structure=assessment.permission_structure(),
            inbound_check=False)
        perms = p.get_permissions()
        if perms["edit"]["assessor"] is False:
            raise ValidationError(f"Assessor cannot be changed, either insufficient permissions or"
                                  f"the  field can't be changed in current status: {assessment.status}")
        return

    def dispatch(self, request, *args, **kwargs):
        self.check_assessment_permissions()
        return super(AssessorViewSet, self).dispatch(request, *args, **kwargs)

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        try:
            serializer = self.get_serializer(queryset.get())
        except Assessor.DoesNotExist:
            return Response(
                _("Assessor does not exist."),
                status.HTTP_404_NOT_FOUND,
            )
        else:
            return Response(serializer.data)


class IndicatorViewSet(
        SafeTenantViewSetMixin,
        mixins.ListModelMixin,
        viewsets.GenericViewSet,
):
    permission_classes = [IsAuthenticated, ]
    queryset = Indicator.objects.filter(active=True).all()
    serializer_class = IndicatorSerializer


class AnswerViewSet(
        SafeTenantViewSetMixin,
        mixins.ListModelMixin,
        mixins.CreateModelMixin,
        mixins.RetrieveModelMixin,
        mixins.UpdateModelMixin,
        viewsets.GenericViewSet,
):
    permission_classes = [IsAuthenticated, ]
    queryset = Answer.objects.all()
    serializer_class = AnswerSerializer

    def get_parent_filter(self):
        parent = self.get_parent_object()
        if not parent:
            return {}

        return {
            'assessment': parent
        }

    def get_object(self):
        queryset = self.get_queryset()
        if "pk" in self.kwargs:
            obj = get_object_or_404(queryset, indicator__pk=self.kwargs["pk"])
        else:
            obj = super().get_object()
        return obj


class AnswerAttachmentsViewSet(
        SafeTenantViewSetMixin,
        mixins.ListModelMixin,
        mixins.CreateModelMixin,
        mixins.RetrieveModelMixin,
        mixins.UpdateModelMixin,
        NestedViewSetMixin,
        viewsets.GenericViewSet,
):
    serializer_class = AnswerAttachmentSerializer
    queryset = Attachment.objects.all()
    permission_classes = [IsAuthenticated, ]

    def get_view_name(self):
        return _('Related Documents')

    def get_parent_object(self):
        return get_object_or_404(
            Answer,
            assessment__pk=self.kwargs.get("nested_1_pk"),
            indicator__pk=self.kwargs.get("nested_2_pk"),
        )

    def get_parent_filter(self):
        parent = self.get_parent_object()
        if not parent:
            return {'code': 'psea_answer'}

        return {
            'content_type_id': ContentType.objects.get_for_model(Answer).pk,
            'object_id': parent.pk,
        }

    def get_object(self, pk=None):
        if pk:
            return self.queryset.get(pk=pk)
        return super().get_object()

    def perform_create(self, serializer):
        serializer.instance = self.get_object(
            pk=serializer.initial_data.get("id")
        )
        serializer.save(content_object=self.get_parent_object())

    def perform_update(self, serializer):
        serializer.save(content_object=self.get_parent_object())
