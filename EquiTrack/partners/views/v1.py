from __future__ import absolute_import
from __future__ import unicode_literals
from collections import namedtuple

from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.views.generic import TemplateView, View
from django.utils.http import urlsafe_base64_decode

from rest_framework import status, viewsets, mixins
from rest_framework.decorators import list_route
from rest_framework.generics import RetrieveAPIView
from rest_framework.response import Response
from easy_pdf.views import PDFTemplateView

from partners.models import (
    FileType,
    PartnerOrganization,
    Agreement,
    PartnerStaffMember,
    IndicatorReport,
)
from partners.exports import (
    PartnerExport,
)
from partners.filters import PartnerOrganizationExportFilter
from partners.permissions import PartnerPermission
from partners.serializers.v1 import (
    FileTypeSerializer,
    PartnerStaffMemberPropertiesSerializer,
    IndicatorReportSerializer,
    PartnerOrganizationSerializer,
    PartnerStaffMemberSerializer,
)
from EquiTrack.utils import get_data_from_insight


class PCAPDFView(PDFTemplateView):
    template_name = "partners/pca/english_pdf.html"
    # TODO add proper templates for different languages
    language_templates_mapping = {
        "arabic": "partners/pca/arabic_pdf.html",
        "english": "partners/pca/english_pdf.html",
        "french": "partners/pca/french_pdf.html",
        "portuguese": "partners/pca/portuguese_pdf.html",
        "russian": "partners/pca/russian_pdf.html",
        "spanish": "partners/pca/spanish_pdf.html",
        "ifrc_english": "partners/pca/ifrc_english_pdf.html",
        "ifrc_french": "partners/pca/ifrc_french_pdf.html"
    }

    def get_context_data(self, **kwargs):
        agr_id = self.kwargs.get('agr')
        lang = self.request.GET.get('lang', None)
        error = None

        try:
            self.template_name = self.language_templates_mapping[lang]
        except KeyError:
            return {"error": "Cannot find document with given query parameter lang={}".format(lang)}

        try:
            agreement = Agreement.objects.get(id=agr_id)
        except Agreement.DoesNotExist:
            return {"error": 'Agreement with specified ID does not exist'}

        if not agreement.partner.vendor_number:
            return {"error": "Partner Organization has no vendor number stored, please report to an etools focal point"}

        valid_response, response = get_data_from_insight('GetPartnerDetailsInfo_json/{vendor_code}',
                                                         {"vendor_code": agreement.partner.vendor_number})

        if not valid_response:
            return {"error": response}
        try:
            banks_records = response["ROWSET"]["ROW"]["VENDOR_BANK"]["VENDOR_BANK_ROW"]
        except (KeyError, TypeError):
            return {"error": 'Response returned by the Server does not have the necessary values to generate PCA'}

        bank_key_values = [
            ('bank_address', "BANK_ADDRESS"),
            ('bank_name', 'BANK_NAME'),
            ('account_title', "ACCT_HOLDER"),
            ('routing_details', "SWIFT_CODE"),
            ('account_number', "BANK_ACCOUNT_NO")
        ]
        Bank = namedtuple('Bank', ' '.join([i[0] for i in bank_key_values]))
        bank_objects = []
        for b in banks_records:
            b["BANK_ADDRESS"] = '{}, {}'.format(b['STREET'], b['CITY'])
            bank_objects.append(Bank(*[b[i[1]] for i in bank_key_values]))

        officers_list = []
        for officer in agreement.authorized_officers.all():
            officers_list.append(
                {'first_name': officer.first_name,
                 'last_name': officer.last_name,
                 'email': officer.email,
                 'title': officer.title}
            )

        font_path = settings.SITE_ROOT + '/assets/fonts/'

        return super(PCAPDFView, self).get_context_data(
            error=error,
            pagesize="Letter",
            title="Partnership",
            agreement=agreement,
            bank_details=bank_objects,
            cp=agreement.country_programme,
            auth_officers=officers_list,
            country=self.request.tenant.long_name,
            font_path=font_path,
            **kwargs
        )


class PortalDashView(View):

    def get(self, request):
        with open(settings.SITE_ROOT + '/templates/frontend/partner/partner.html', 'r') as my_f:
            result = my_f.read()
        return HttpResponse(result)


class PortalLoginFailedView(TemplateView):

    template_name = "partner_loginfailed.html"

    def get_context_data(self, **kwargs):
        context = super(PortalLoginFailedView, self).get_context_data(**kwargs)
        context['email'] = urlsafe_base64_decode(context['email'])
        return context


class PartnerStaffMemberPropertiesView(RetrieveAPIView):
    """
    Gets the details of Staff Member belonging to a partner
    """
    serializer_class = PartnerStaffMemberPropertiesSerializer
    queryset = PartnerStaffMember.objects.all()

    def get_object(self):
        queryset = self.get_queryset()
        # TODO: see permissions if user is staff allow access to all partners (maybe)

        # Get the current partnerstaffmember
        try:
            current_member = PartnerStaffMember.objects.get(id=self.request.user.profile.partner_staff_member)
        except PartnerStaffMember.DoesNotExist:
            raise Exception('there is no PartnerStaffMember record associated with this user')

        # Perform the lookup filtering.
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
        # If current member is actually looking for themselves return right away.
        if self.kwargs[lookup_url_kwarg] == str(current_member.id):
            return current_member

        filter = {self.lookup_field: self.kwargs[lookup_url_kwarg]}
        # allow lookup only for PSMs inside the same partnership
        filter['partner'] = current_member.partner

        obj = get_object_or_404(queryset, **filter)
        self.check_object_permissions(self.request, obj)
        return obj


class IndicatorReportViewSet(
        mixins.RetrieveModelMixin,
        mixins.CreateModelMixin,
        mixins.ListModelMixin,
        viewsets.GenericViewSet):
    """
    Returns a list of all Indicator Reports for an Intervention and Result
    """
    model = IndicatorReport
    queryset = IndicatorReport.objects.all()
    serializer_class = IndicatorReportSerializer
    # permission_classes = (IndicatorReportPermission,)

    def get_serializer(self, *args, **kwargs):
        if "data" in kwargs:
            data = kwargs["data"]

            if isinstance(data, list):
                kwargs["many"] = True

        return super(IndicatorReportViewSet, self).get_serializer(*args, **kwargs)

    def perform_create(self, serializer):
        # add the user to the arguments
        try:
            partner_staff_member = PartnerStaffMember.objects.get(
                pk=self.request.user.profile.partner_staff_member
            )
        except PartnerStaffMember.DoesNotExist:
            raise Exception('User without partnerstaffmember set is trying to submit a report')

        serializer.save(partner_staff_member=partner_staff_member)

    def retrieve(self, request, partner_pk=None, intervention_pk=None, result_pk=None, pk=None):
        """
        Returns an Indicator report object
        """
        try:
            queryset = self.queryset.get(id=pk)
            serializer = self.serializer_class(queryset)
            data = serializer.data
        except IndicatorReport.DoesNotExist:
            data = {}
        return Response(
            data,
            status=status.HTTP_200_OK
        )


class PartnerOrganizationsViewSet(
        mixins.RetrieveModelMixin,
        mixins.ListModelMixin,
        mixins.CreateModelMixin,
        mixins.UpdateModelMixin,
        viewsets.GenericViewSet):
    """
    Returns a list of all Partner Organizations
    """
    queryset = PartnerOrganization.objects.all()
    serializer_class = PartnerOrganizationSerializer
    permission_classes = (PartnerPermission,)
    filter_backends = (PartnerOrganizationExportFilter,)

    def create(self, request, *args, **kwargs):
        """
        Add a Partner Organization
        :return: JSON
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        serializer.instance = serializer.save()

        headers = self.get_success_headers(serializer.data)
        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED,
            headers=headers
        )

    @list_route(methods=['get'])
    def export(self, request):
        queryset = self.get_queryset()
        queryset = self.filter_queryset(queryset)
        dataset = PartnerExport().export(queryset)

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="ModelExportPartners.csv"'
        response.write(dataset.csv)
        return response


class PartnerStaffMembersViewSet(
        mixins.RetrieveModelMixin,
        mixins.ListModelMixin,
        mixins.CreateModelMixin,
        viewsets.GenericViewSet):
    """
    Returns a list of all Partner staff members
    """
    queryset = PartnerStaffMember.objects.all()
    serializer_class = PartnerStaffMemberSerializer
    permission_classes = (PartnerPermission,)

    def create(self, request, *args, **kwargs):
        """
        Add Staff member to Partner Organization
        :return: JSON
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        serializer.instance = serializer.save()

        headers = self.get_success_headers(serializer.data)
        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED,
            headers=headers
        )

    def retrieve(self, request, partner_pk=None, pk=None):
        queryset = self.queryset.get(partner_id=partner_pk, id=pk)
        serializer = self.serializer_class(queryset)
        return Response(
            serializer.data,
            status=status.HTTP_200_OK
        )


class FileTypeViewSet(
        mixins.RetrieveModelMixin,
        mixins.ListModelMixin,
        mixins.CreateModelMixin,
        viewsets.GenericViewSet):
    """
    Returns a list of all Partner file types
    """
    queryset = FileType.objects.all()
    serializer_class = FileTypeSerializer
