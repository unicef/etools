from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.db.models import ObjectDoesNotExist, Q
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from django_filters.rest_framework import DjangoFilterBackend
from easy_pdf.rendering import render_to_pdf_response
from etools_validator.mixins import ValidatorViewMixin
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from unicef_attachments.models import Attachment
from unicef_rest_export.renderers import ExportCSVRenderer, ExportOpenXMLRenderer
from unicef_rest_export.views import ExportMixin
from unicef_restlib.pagination import DynamicPageNumberPagination
from unicef_restlib.views import NestedViewSetMixin, QueryStringFilterMixin, SafeTenantViewSetMixin

from etools.applications.action_points.conditions import (
    ActionPointAssignedByCondition,
    ActionPointAssigneeCondition,
    ActionPointAuthorCondition,
)
from etools.applications.audit.models import UNICEFAuditFocalPoint
from etools.applications.partners.views.v2 import choices_to_json_ready
from etools.applications.permissions2.conditions import ObjectStatusCondition
from etools.applications.permissions2.drf_permissions import NestedPermission
from etools.applications.permissions2.metadata import PermissionBasedMetadata
from etools.applications.permissions2.views import PermittedSerializerMixin
from etools.applications.psea.conditions import PSEAModuleCondition
from etools.applications.psea.models import Answer, Assessment, AssessmentActionPoint, Assessor, Indicator
from etools.applications.psea.permissions import AssessmentPermissions
from etools.applications.psea.renderers import AssessmentActionPointCSVRenderer
from etools.applications.psea.serializers import (
    AnswerAttachmentSerializer,
    AnswerSerializer,
    AssessmentActionPointExportSerializer,
    AssessmentActionPointSerializer,
    AssessmentDetailExportSerializer,
    AssessmentDetailSerializer,
    AssessmentExportSerializer,
    AssessmentSerializer,
    AssessmentStatusHistorySerializer,
    AssessmentStatusSerializer,
    AssessorSerializer,
    IndicatorSerializer,
)
from etools.applications.psea.validation import AssessmentValid


class PSEAStaticDropdownsListAPIView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        """Return All Static values used for dropdowns in the frontend"""

        return Response(
            {
                'ratings': choices_to_json_ready(Assessment.RATING),
                'types': choices_to_json_ready(Assessment.ASSESSMENT_TYPES),
                'ingo_reasons': choices_to_json_ready(Assessment.INGO_REASONS),
            },
            status=status.HTTP_200_OK
        )


class AssessmentViewSet(
        SafeTenantViewSetMixin,
        ValidatorViewMixin,
        QueryStringFilterMixin,
        ExportMixin,
        mixins.CreateModelMixin,
        mixins.ListModelMixin,
        mixins.UpdateModelMixin,
        mixins.RetrieveModelMixin,
        PermittedSerializerMixin,
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
            'assessor__auditor_firm__organization__name__icontains',
            'assessor__user__first_name__icontains',
            'assessor__user__last_name__icontains',
        ]),
        ('partner', 'partner_id__in'),
        ('sea_risk_rating', {
            'high': [('overall_rating__gte', 0), ('overall_rating__lte', 8)],
            'moderate': [('overall_rating__gte', 9), ('overall_rating__lte', 14)],
            'low': [('overall_rating__gte', 15), ],
        }),
        ('status', 'status__in'),
        ('unicef_focal_point', 'focal_points__pk__in'),
        ('assessment_date__lt', 'assessment_date__lt'),
        ('assessment_date__gt', 'assessment_date__gt'),
        ('assessor_staff', 'assessor__user__pk__in'),
        ('assessor_external', 'assessor__user__pk__in'),
        ('assessor_firm', 'assessor__auditor_firm__pk__in'),
    )
    export_filename = 'Assessment'

    SERIALIZER_MAP = {
        "status_history": AssessmentStatusHistorySerializer,
    }

    def parse_sort_params(self):
        MAP_SORT = {
            "reference_number": "reference_number",
            "assessment_date": "assessment_date",
            "partner_name": "partner__organization__name",
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
        user = self.request.user
        # if the user is not unicef, filter only what they can see
        if not user.is_unicef_user():
            qs = qs.filter(Q(assessor__auditor_firm_staff__user=user) | Q(assessor__user=user))
        if "sort" in self.request.GET:
            qs = qs.order_by(*self.parse_sort_params())
        return qs

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        if not request.user.groups.filter(
                name__in=[UNICEFAuditFocalPoint.name]
        ).exists():
            return HttpResponseForbidden()

        related_fields = []
        nested_related_names = []
        serializer = self.my_create(
            request,
            related_fields,
            nested_related_names=nested_related_names,
            **kwargs,
        )

        instance = serializer.instance

        validator = AssessmentValid(instance, user=request.user)
        if not validator.is_valid:
            raise ValidationError(validator.errors)

        headers = self.get_success_headers(serializer.data)
        if getattr(instance, '_prefetched_objects_cache', None):
            # If 'prefetch_related' has been applied to a queryset, we need to
            # refresh the instance from the database.
            instance = self.get_object()
        return Response(
            AssessmentDetailSerializer(
                instance,
                context=self.get_serializer_context(),
            ).data,
            status=status.HTTP_201_CREATED,
            headers=headers
        )

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        related_fields = ["status_history"]
        nested_related_names = []
        related_non_serialized_fields = ["focal_points"]

        # FIXME move to etools_validator library
        # store old related field data
        instance = self.get_object()
        old_related_data = []
        for field in related_non_serialized_fields:
            try:
                rel_field_val = getattr(instance, field)
            except ObjectDoesNotExist:
                pass
            else:
                prop = f"{field}_old"

                try:
                    val = list(rel_field_val.all())
                except AttributeError:
                    # This means OneToOne field
                    val = rel_field_val

                old_related_data.append((prop, val))

        instance, old_instance, serializer = self.my_update(
            request,
            related_fields,
            nested_related_names=nested_related_names,
            **kwargs
        )

        # FIXME move to etools_validator library
        # add old related field data to old instance
        for field, val in old_related_data:
            setattr(old_instance, field, val)

        validator = AssessmentValid(
            instance,
            old=old_instance,
            user=request.user,
        )
        if not validator.is_valid:
            raise ValidationError(validator.errors)

        if getattr(instance, '_prefetched_objects_cache', None):
            # If 'prefetch_related' has been applied to a queryset, we need to
            # refresh the instance from the database.
            instance = self.get_object()

        return Response(
            AssessmentDetailSerializer(
                instance,
                context=self.get_serializer_context(),
            ).data
        )

    def _set_status(self, request, assessment_status, **kwargs):
        self.serializer_class = AssessmentStatusSerializer
        status = {
            "status": assessment_status,
        }
        comment = request.data.get("comment")
        if comment:
            status["comment"] = comment
        request.data.clear()
        if 'nfr_attachment' in kwargs:
            request.data.update({"nfr_attachment": kwargs.get('nfr_attachment')})
        request.data.update({"status": assessment_status})
        request.data.update(
            {"status_history": [status]},
        )
        return self.update(request, partial=True)

    def retrieve(self, request, *args, **kwargs):
        self.serializer_class = AssessmentDetailSerializer
        return super().retrieve(request, *args, **kwargs)

    @action(detail=True, methods=["patch"])
    def assign(self, request, pk=None):
        return self._set_status(request, Assessment.STATUS_ASSIGNED)

    @action(detail=True, methods=["patch"])
    def submit(self, request, pk=None):
        return self._set_status(request, Assessment.STATUS_SUBMITTED)

    @action(detail=True, methods=["patch"])
    def finalize(self, request, pk=None):
        return self._set_status(request, Assessment.STATUS_FINAL, **request.data)

    @action(detail=True, methods=["patch"])
    def cancel(self, request, pk=None):
        return self._set_status(request, Assessment.STATUS_CANCELLED)

    @action(detail=True, methods=["patch"])
    def reject(self, request, pk=None):
        return self._set_status(request, Assessment.STATUS_REJECTED)

    @action(
        detail=False,
        methods=['get'],
        url_path='export/xlsx',
        renderer_classes=(ExportOpenXMLRenderer,),
    )
    def list_export_xlsx(self, request, *args, **kwargs):
        self.serializer_class = AssessmentExportSerializer
        assessments = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(assessments, many=True)
        return Response(serializer.data, headers={
            'Content-Disposition': 'attachment;filename=assessments_{}.xlsx'.format(
                timezone.now().date(),
            )
        })

    @action(
        detail=True,
        methods=['get'],
        url_path='export/xlsx',
        renderer_classes=(ExportOpenXMLRenderer,),
    )
    def single_export_xlsx(self, request, *args, **kwargs):

        qs = Answer.objects.filter(assessment=self.get_object()).prefetch_related('evidences', 'attachments').order_by(
            'indicator__pk')
        if qs.exists():
            self.serializer_class = AssessmentDetailExportSerializer
            serializer = self.get_serializer(qs, many=True)
        else:
            self.serializer_class = AssessmentExportSerializer
            serializer = self.get_serializer([self.get_object()], many=True)
        return Response(serializer.data, headers={
            'Content-Disposition': 'attachment;filename={}_{}.xlsx'.format(
                self.get_object().reference_number, timezone.now().date()
            )
        })

    @action(
        detail=True,
        methods=['get'],
        url_path='export/pdf',
    )
    def single_export_pdf(self, request, *args, **kwargs):
        qs = Answer.objects.filter(assessment=self.get_object()).prefetch_related('evidences', 'attachments').order_by(
            'indicator__pk')
        ctx = {'obj': self.get_object(), 'qs': qs, 'request': request, 'pagesize': "A4 landscape"}
        return render_to_pdf_response(
            request=self.request, template='psea_pdf.html', context=ctx, filename='export.pdf')

    @action(
        detail=False,
        methods=['get'],
        url_path='export/csv',
        renderer_classes=(ExportCSVRenderer,),
    )
    def list_export_csv(self, request, *args, **kwargs):
        self.serializer_class = AssessmentExportSerializer
        assessments = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(assessments, many=True)
        return Response(serializer.data, headers={
            'Content-Disposition': 'attachment;filename=assessments_{}.csv'.format(
                timezone.now().date(),
            )
        })

    @action(
        detail=True,
        methods=['get'],
        url_path='export/csv',
        renderer_classes=(ExportCSVRenderer,),
    )
    def single_export_csv(self, request, *args, **kwargs):
        qs = Answer.objects.filter(assessment=self.get_object()).prefetch_related('evidences', 'attachments').order_by(
            'indicator__pk')
        if qs.exists():
            self.serializer_class = AssessmentDetailExportSerializer
            serializer = self.get_serializer(qs, many=True)
        else:
            self.serializer_class = AssessmentExportSerializer
            serializer = self.get_serializer([self.get_object()], many=True)
        return Response(serializer.data, headers={
            'Content-Disposition': 'attachment;filename={}_{}.csv'.format(
                self.get_object().reference_number, timezone.now().date()
            )
        })


class AssessmentActionPointViewSet(
        SafeTenantViewSetMixin,
        PermittedSerializerMixin,
        mixins.ListModelMixin,
        mixins.CreateModelMixin,
        mixins.RetrieveModelMixin,
        mixins.UpdateModelMixin,
        NestedViewSetMixin,
        viewsets.GenericViewSet,
):
    metadata_class = PermissionBasedMetadata
    queryset = AssessmentActionPoint.objects.all()
    serializer_class = AssessmentActionPointSerializer
    permission_classes = [IsAuthenticated, NestedPermission]

    def get_permission_context(self):
        context = super().get_permission_context()
        context.append(PSEAModuleCondition())
        return context

    def get_obj_permission_context(self, obj):
        context = super().get_obj_permission_context(obj)
        context.extend([
            ObjectStatusCondition(obj),
            ActionPointAuthorCondition(obj, self.request.user),
            ActionPointAssignedByCondition(obj, self.request.user),
            ActionPointAssigneeCondition(obj, self.request.user),
        ])
        return context

    @action(
        detail=False,
        methods=['get'],
        url_path='export',
        renderer_classes=(AssessmentActionPointCSVRenderer,),
    )
    def csv_export(self, request, *args, **kwargs):
        serializer = AssessmentActionPointExportSerializer(
            self.filter_queryset(self.get_queryset()),
            many=True,
        )
        return Response(serializer.data, headers={
            'Content-Disposition': 'attachment;filename={}_action_points_{}.csv'.format(
                self.get_root_object().reference_number, timezone.now().date()
            )
        })


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

    def check_assessment_permissions(self, user):
        try:
            assessment = Assessment.objects.get(
                pk=self.kwargs.get("nested_1_pk"),
            )
        except Assessment.DoesNotExist:
            raise ValidationError("Assessment object id incorrect")
        p = AssessmentPermissions(
            user=user,
            instance=assessment,
            permission_structure=assessment.permission_structure(),
            inbound_check=False)
        perms = p.get_permissions()
        if perms["edit"]["assessor"] is False:
            raise ValidationError(
                f"Assessor cannot be changed, either insufficient permissions"
                f" or the field can't be changed in current status: "
                f"{assessment.status}",
            )
        return

    def create(self, request, *args, **kwargs):
        self.check_assessment_permissions(request.user)
        return super().create(request, *args, **kwargs)

    def update(self, request, pk=None, *args, **kwargs):
        self.check_assessment_permissions(request.user)
        return super().update(request, pk, *args, **kwargs)

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


class AnswerBaseViewSet(
        SafeTenantViewSetMixin,
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


class AnswerListViewSet(
        AnswerBaseViewSet,
        mixins.ListModelMixin,
        viewsets.GenericViewSet,
):
    def get_queryset(self):
        return super().get_queryset().filter(
            assessment__pk=self.kwargs.get("nested_1_pk"),
        )


class AnswerViewSet(
        AnswerBaseViewSet,
        mixins.CreateModelMixin,
        mixins.RetrieveModelMixin,
        mixins.UpdateModelMixin,
        mixins.DestroyModelMixin,
        viewsets.GenericViewSet,
):
    def get_object(self):
        queryset = self.get_queryset()
        return get_object_or_404(
            queryset,
            assessment__pk=self.kwargs.get("nested_1_pk"),
            indicator__pk=self.kwargs["pk"],
        )

    def check_assessment_permissions(self, user):
        try:
            assessment = Assessment.objects.get(
                pk=self.kwargs.get("nested_1_pk"),
            )
        except Assessment.DoesNotExist:
            raise ValidationError("Assessment object id incorrect")
        p = AssessmentPermissions(
            user=user,
            instance=assessment,
            permission_structure=assessment.permission_structure(),
            inbound_check=True)
        perms = p.get_permissions()
        if perms["edit"]["answers"] is False:
            raise ValidationError(
                f"Answers cannot be changed, either insufficient permissions"
                f" or the field can't be changed in current status: "
                f"{assessment.status}",
            )
        return

    def post(self, request, *arg, **kwargs):
        self.check_assessment_permissions(request.user)
        request.data["indicator"] = kwargs.get("pk")
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED,
            headers=headers,
        )


class AnswerAttachmentsViewSet(
        SafeTenantViewSetMixin,
        mixins.ListModelMixin,
        mixins.CreateModelMixin,
        mixins.RetrieveModelMixin,
        mixins.UpdateModelMixin,
        mixins.DestroyModelMixin,
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
