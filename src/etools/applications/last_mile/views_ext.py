from django.contrib.auth import get_user_model
from django.http import StreamingHttpResponse

from django_filters import rest_framework as filters
from rest_framework import status
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from etools.applications.last_mile.filters_ext import UserFilter
from etools.applications.last_mile.permissions import LMSMAPIPermission
from etools.applications.last_mile.serializers_ext import (
    IngestRowSerializer,
    MaterialIngestResultSerializer,
    MaterialIngestSerializer,
    TransferIngestResultSerializer,
    UserListSerializer,
)
from etools.applications.last_mile.services_ext import (
    DataExportService,
    InvalidDateFormatError,
    InvalidModelTypeError,
    MaterialIngestService,
    TransferIngestService,
)
from etools.applications.last_mile.utils_ext import stream_queryset_as_json


class VisionIngestMaterialsApiView(APIView):
    permission_classes = (LMSMAPIPermission,)

    def post(self, request):
        input_serializer = MaterialIngestSerializer(data=request.data, many=True)
        input_serializer.is_valid(raise_exception=True)

        ingest_result = MaterialIngestService().ingest_materials(
            validated_data=input_serializer.validated_data
        )

        output_serializer = MaterialIngestResultSerializer(ingest_result)

        return Response(output_serializer.data, status=status.HTTP_200_OK)


class VisionUsersExport(ListAPIView):
    permission_classes = (LMSMAPIPermission,)
    serializer_class = UserListSerializer
    filter_backends = [filters.DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = UserFilter
    search_fields = ['email', 'first_name', 'last_name', 'profile__vendor_number']
    ordering_fields = ['email', 'first_name', 'last_name', 'profile__vendor_number']
    ordering = ['email']

    def get_queryset(self):
        workspace = self.request.query_params.get('workspace')
        role = self.request.query_params.get('role')

        if not workspace or not role:
            return get_user_model().objects.none()

        return get_user_model().objects.select_related('profile').prefetch_related(
            'realms__country',
            'realms__group'
        ).filter(is_active=True)

    def list(self, request, *args, **kwargs):
        workspace = request.query_params.get('workspace')
        role = request.query_params.get('role')

        if not workspace or not role:
            return Response(
                {
                    "error": "Both 'workspace' and 'role' filters are required.",
                    "detail": "Please provide both workspace and role query parameters."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        return super().list(request, *args, **kwargs)


class VisionLMSMExport(APIView):
    permission_classes = (LMSMAPIPermission,)

    def get(self, request, *args, **kwargs):
        model_type = request.query_params.get('type')
        last_modified = request.query_params.get('last_modified')

        if not model_type:
            return Response({"type": "This field is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            service = DataExportService()
            queryset = service.get_export_queryset(
                model_type=model_type,
                last_modified=last_modified
            )

        except InvalidModelTypeError as e:
            return Response({"type": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except InvalidDateFormatError as e:
            return Response({"last_modified": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        response = StreamingHttpResponse(
            stream_queryset_as_json(queryset),
            content_type='application/json'
        )

        return response


class VisionIngestTransfersApiView(APIView):
    permission_classes = (LMSMAPIPermission,)

    def post(self, request):

        # Filter for relevant events before any processing (At the moment we care only about LD events)
        relevant_data = [row for row in request.data if row.get('Event') == 'LD']

        if not relevant_data:
            return Response(
                {"detail": "No rows with Event 'LD' found in the payload."},
                status=status.HTTP_200_OK
            )

        input_serializer = IngestRowSerializer(data=relevant_data, many=True)
        input_serializer.is_valid(raise_exception=True)

        service = TransferIngestService()
        ingest_report = service.ingest_validated_data(input_serializer.validated_data)

        output_serializer = TransferIngestResultSerializer(ingest_report)

        return Response(output_serializer.data, status=status.HTTP_200_OK)
