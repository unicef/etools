from __future__ import absolute_import

import datetime

from rest_framework.decorators import detail_route

__author__ = 'jcranwellward'


from django.views.generic import TemplateView, View
from django.utils.http import urlsafe_base64_decode
from django.http import HttpResponse
from django.conf import settings
from django.shortcuts import get_object_or_404

from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework import viewsets, mixins
from easy_pdf.views import PDFTemplateView

from locations.models import Location
from .serializers import (
    FileTypeSerializer,
    LocationSerializer,
    PartnerStaffMemberPropertiesSerializer,
    InterventionSerializer,
    ResultChainDetailsSerializer,
    IndicatorReportSerializer,
    PCASectorSerializer,
    PCAGrantSerializer,
    AmendmentLogSerializer,
    GWLocationSerializer,
    PartnerOrganizationSerializer,
    PartnerStaffMemberSerializer,
    AgreementSerializer,
    PartnershipBudgetSerializer,
    PCAFileSerializer
)
from .permissions import PartnerPermission, ResultChainPermission
from rest_framework.parsers import MultiPartParser, FormParser

from .models import (
    FileType,
    PartnershipBudget,
    PCAFile,
    AuthorizedOfficer,
    PCA,
    PartnerOrganization,
    Agreement,
    PCAGrant,
    AmendmentLog,
    PCASector,
    GwPCALocation,
    PartnerStaffMember,
    ResultChain,
    IndicatorReport
)
from reports.models import ResultStructure
from rest_framework import status
from rest_framework.response import Response


class PcaPDFView(PDFTemplateView):
    template_name = "partners/pca_pdf.html"

    def get_context_data(self, **kwargs):
        agr_id = self.kwargs.get('agr')
        agreement = Agreement.objects.get(id=agr_id)
        officers = agreement.authorized_officers.all()
        officers_list = []
        for officer in officers:
            officers_list.append(
                {'first_name': officer.officer.first_name,
                 'last_name': officer.officer.last_name,
                 'title': officer.officer.title}
            )

        return super(PcaPDFView, self).get_context_data(
            pagesize="Letter",
            title="Partnership",
            agreement=agreement,
            cp=ResultStructure.current(),
            auth_officers=officers_list,
            country=self.request.tenant.name,
            **kwargs
        )


class InterventionLocationView(ListAPIView):
    """
    Gets a list of Intervention locations based on passed query params
    """
    model = GwPCALocation
    serializer_class = LocationSerializer

    def get_queryset(self):
        """
        Return locations with GPS points only
        """
        status = self.request.query_params.get('status', PCA.ACTIVE)
        result_structure = self.request.query_params.get('result_structure', None)
        sector = self.request.query_params.get('sector', None)
        gateway = self.request.query_params.get('gateway', None)
        governorate = self.request.query_params.get('governorate', None)
        donor = self.request.query_params.get('donor', None)
        partner = self.request.query_params.get('partner', None)
        district = self.request.query_params.get('district', None)

        queryset = self.model.objects.filter(
            pca__status=status,
        )

        if gateway is not None:
            queryset = queryset.filter(
                location__gateway__id=int(gateway)
            )
        if governorate is not None:
            queryset = queryset.filter(
                governorate__id=int(governorate)
            )
        if district is not None:
            queryset = queryset.filter(
                region__id=int(district)
            )
        if result_structure is not None:
            queryset = queryset.filter(
                pca__result_structure__id=int(result_structure)
            )
        if partner is not None:
            queryset = queryset.filter(
                pca__partner__id=int(partner)
            )
        if sector is not None:
            # get the filtered pcas so far
            pcas = queryset.values_list('pca__id', flat=True)
            # get those that contain this sector
            pcas = PCASector.objects.filter(
                pca__in=pcas,
                sector__id=int(sector)
            ).values_list('pca__id', flat=True)
            # now filter the current query by the selected ids
            queryset = queryset.filter(
                pca__id__in=pcas
            )

        if donor is not None:
            # get the filtered pcas so far
            pcas = queryset.values_list('pca__id', flat=True)
            # get those that contain this donor
            pcas = PCAGrant.objects.filter(
                pca__id__in=pcas,
                grant__donor__id=int(donor)
            ).values_list('pca', flat=True)
            # now filter the current query by the selected ids
            queryset = queryset.filter(
                pca__id__in=pcas
            )

        pca_locs = queryset.values_list('location', flat=True)
        locs = Location.objects.filter(
            id__in=pca_locs
        )
        return locs


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


class AgreementViewSet(mixins.RetrieveModelMixin,
                       mixins.ListModelMixin,
                       mixins.CreateModelMixin,
                       viewsets.GenericViewSet):
    """
    Returns a list of Agreements
    """
    queryset = Agreement.objects.all()
    serializer_class = AgreementSerializer
    permission_classes = (PartnerPermission,)

    def create(self, request, *args, **kwargs):
        """
        Add a new Agreement
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

    @detail_route(methods=['get'], url_path='interventions')
    def interventions(self, request, partner_pk=None, pk =None):
        """
        Return All Interventions for Partner and Agreement
        """
        data = PCA.objects.filter(partner_id=partner_pk, agreement_id=pk).values()
        headers = self.get_success_headers(data)
        return Response(
            data,
            status=status.HTTP_200_OK,
            headers=headers
        )

    def get_queryset(self):

        queryset = super(AgreementViewSet, self).get_queryset()
        if not self.request.user.is_staff:
            # This must be a partner
            try:
                # TODO: Promote this to a permissions class
                current_member = PartnerStaffMember.objects.get(
                    id=self.request.user.profile.partner_staff_member
                )
            except PartnerStaffMember.DoesNotExist:
                # This is an authenticated user with no access to interventions
                return queryset.none()
            else:
                # Return all interventions this partner has
                return queryset.filter(partner=current_member.partner)
        return queryset

    def retrieve(self, request, partner_pk=None, pk=None):
        """
        Returns an Agreement object for this Agreement PK and partner
        """
        try:
            queryset = self.queryset.get(partner=partner_pk, id=pk)
            serializer = self.serializer_class(queryset)
            data = serializer.data
        except Agreement.DoesNotExist:
            data = {}
        return Response(
            data,
            status=status.HTTP_200_OK
        )


class InterventionsViewSet(mixins.RetrieveModelMixin,
                           mixins.ListModelMixin,
                           mixins.CreateModelMixin,
                           viewsets.GenericViewSet):
    """
    Returns a list of all Interventions,
    """
    queryset = PCA.objects.all()
    serializer_class = InterventionSerializer
    permission_classes = (PartnerPermission,)

    def create(self, request, *args, **kwargs):
        """
        Add an Intervention
        :return: JSON
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            managers = request.data['unicef_managers']
        except KeyError:
            managers = []

        serializer.instance = serializer.save()
        try:
            serializer.instance.created_at = datetime.datetime.strptime(request.data['created_at'], '%Y-%m-%dT%H:%M:%S.%fZ')
        except Exception:
            serializer.instance.created_at = datetime.datetime.strptime(request.data['created_at'], '%Y-%m-%dT%H:%M:%SZ')
        serializer.instance.updated_at = datetime.datetime.strptime(request.data['updated_at'], '%Y-%m-%dT%H:%M:%S.%fZ')
        serializer.instance.save()
        data = serializer.data

        for man in managers:
            serializer.instance.unicef_managers.add(man)

        headers = self.get_success_headers(data)
        return Response(data, status=status.HTTP_201_CREATED,
                        headers=headers)

    def get_queryset(self):

        queryset = super(InterventionsViewSet, self).get_queryset()
        if not self.request.user.is_staff:
            # This must be a partner
            try:
                # TODO: Promote this to a permissions class
                current_member = PartnerStaffMember.objects.get(
                    id=self.request.user.profile.partner_staff_member
                )
            except PartnerStaffMember.DoesNotExist:
                # This is an authenticated user with no access to interventions
                return queryset.none()
            else:
                # Return all interventions this partner has
                return queryset.filter(partner=current_member.partner)
        return queryset

    def retrieve(self, request, partner_pk=None, pk=None):
        """
        Returns an Intervention object for this Intervention PK and partner
        """
        try:
            queryset = self.queryset.get(partner_id=partner_pk, id=pk)
            serializer = self.serializer_class(queryset)
            data = serializer.data
        except PCA.DoesNotExist:
            data = {}
        return Response(
            data,
            status=status.HTTP_200_OK
        )


class ResultChainViewSet(mixins.RetrieveModelMixin,
                         mixins.ListModelMixin,
                         viewsets.GenericViewSet):
    """
    Returns a list of all Result Chain for an Intervention
    """
    model = ResultChain
    queryset = ResultChain.objects.all()
    serializer_class = ResultChainDetailsSerializer
    permission_classes = (ResultChainPermission,)

    def get_queryset(self):
        queryset = super(ResultChainViewSet, self).get_queryset()
        intervention_id = self.kwargs.get('intervention_pk')
        return queryset.filter(partnership_id=intervention_id)

    def retrieve(self, request, partner_pk=None, intervention_pk=None, pk=None):
        """
        Returns an Intervention object for this Intervention PK and partner
        """
        try:
            queryset = self.queryset.get(partnership_id=intervention_pk, id=pk)
            serializer = self.serializer_class(queryset)
            data = serializer.data
        except ResultChain.DoesNotExist:
            data = {}
        return Response(
            data,
            status=status.HTTP_200_OK
        )


class IndicatorReportViewSet(mixins.RetrieveModelMixin,
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

    def perform_create(self, serializer):
        # add the user to the arguments
        try:
            partner_staff_member = PartnerStaffMember.objects.get(
                pk=self.request.user.profile.partner_staff_member
            )
        except PartnerStaffMember.DoesNotExist:
            raise Exception('Hell')

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


class PCASectorViewSet(mixins.RetrieveModelMixin,
                             mixins.CreateModelMixin,
                             mixins.ListModelMixin,
                             viewsets.GenericViewSet):
    """
    Returns a list of Sectors for an Interventions (PCA)
    """
    model = PCASector
    queryset = PCASector.objects.all()
    serializer_class = PCASectorSerializer
    permission_classes = (ResultChainPermission,)

    def create(self, request, *args, **kwargs):
        """
        Add a Sector to the PCA
        :return: JSON
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        serializer.instance = serializer.save()
        serializer.instance.created = datetime.datetime.strptime(request.data['created'], '%Y-%m-%dT%H:%M:%S.%fZ')
        serializer.instance.modified = datetime.datetime.strptime(request.data['modified'], '%Y-%m-%dT%H:%M:%S.%fZ')
        serializer.instance.save()
        data = serializer.data

        headers = self.get_success_headers(data)
        return Response(data, status=status.HTTP_201_CREATED,
                        headers=headers)

    def get_queryset(self):

        queryset = super(PCASectorViewSet, self).get_queryset()
        intervention_id = self.kwargs.get('intervention_pk')
        return queryset.filter(pca=intervention_id)

    def retrieve(self, request, partner_pk=None, intervention_pk=None, pk=None):
        """
        Returns a PCA Sector object
        """
        try:
            queryset = self.queryset.get(pca_id=intervention_pk, id=pk)
            serializer = self.serializer_class(queryset)
            data = serializer.data
        except PCASector.DoesNotExist:
            data = {}
        return Response(
            data,
            status=status.HTTP_200_OK
        )


class PartnershipBudgetViewSet(mixins.RetrieveModelMixin,
                             mixins.CreateModelMixin,
                             mixins.ListModelMixin,
                             viewsets.GenericViewSet):
    """
    Returns a list of partnership Budgets for an Intervention (PCA)
    """
    model = PartnershipBudget
    queryset = PartnershipBudget.objects.all()
    serializer_class = PartnershipBudgetSerializer
    permission_classes = (ResultChainPermission,)

    def create(self, request, *args, **kwargs):
        """
        Add partnership Budget to the PCA
        :return: JSON
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        serializer.instance = serializer.save()
        serializer.instance.created = datetime.datetime.strptime(request.data['created'], '%Y-%m-%dT%H:%M:%S.%fZ')
        serializer.instance.modified = datetime.datetime.strptime(request.data['modified'], '%Y-%m-%dT%H:%M:%S.%fZ')
        serializer.instance.save()
        data = serializer.data

        headers = self.get_success_headers(data)
        return Response(
            data,
            status=status.HTTP_201_CREATED,
            headers=headers
        )

    def get_queryset(self):

        queryset = super(PartnershipBudgetViewSet, self).get_queryset()
        intervention_id = self.kwargs.get('intervention_pk')
        return queryset.filter(partnership_id=intervention_id)

    def retrieve(self, request, partner_pk=None, intervention_pk=None, pk=None):
        """
        Returns a PCA Budget Object
        """
        try:
            queryset = self.queryset.get(partnership_id=intervention_pk, id=pk)
            serializer = self.serializer_class(queryset)
            data = serializer.data
        except PartnershipBudget.DoesNotExist:
            data = {}
        return Response(
            data,
            status=status.HTTP_200_OK
        )


class PCAFileViewSet(mixins.RetrieveModelMixin,
                             mixins.CreateModelMixin,
                             mixins.ListModelMixin,
                             viewsets.GenericViewSet):
    """
    Returns a list of files URL for an Intervention (PCA)
    """
    model = PCAFile
    queryset = PCAFile.objects.all()
    serializer_class = PCAFileSerializer
    # parser_classes = (MultiPartParser, FormParser,)
    permission_classes = (PartnerPermission,)

    def create(self, request, *args, **kwargs):
        """
        Add a file to the PCA
        :return: JSON
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            attachment = request.data["attachment"]
        except KeyError:
            attachment = None

        serializer.instance = serializer.save()

        if attachment:
            serializer.instance.attachment = attachment
            serializer.instance.save()

        headers = self.get_success_headers(serializer.data)
        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED,
            headers=headers
        )

    def get_queryset(self):

        queryset = super(PCAFileViewSet, self).get_queryset()
        intervention_id = self.kwargs.get('intervention_pk')
        return queryset.filter(pca=intervention_id)

    def retrieve(self, request, partner_pk=None, intervention_pk=None, pk=None):
        """
        Returns a PCA File Object
        """
        try:
            queryset = self.queryset.get(pca_id=intervention_pk, id=pk)
            serializer = self.serializer_class(queryset)
            data = serializer.data
        except PCAFile.DoesNotExist:
            data = {}
        return Response(
            data,
            status=status.HTTP_200_OK
        )


class PCAGrantViewSet(mixins.RetrieveModelMixin,
                             mixins.CreateModelMixin,
                             mixins.ListModelMixin,
                             viewsets.GenericViewSet):
    """
    Returns a list of Grants for a Intervention (PCA)
    """
    model = PCAGrant
    queryset = PCAGrant.objects.all()
    serializer_class = PCAGrantSerializer
    permission_classes = (ResultChainPermission,)

    def create(self, request, *args, **kwargs):
        """
        Add a Grant to the PCA
        :return: JSON
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        serializer.instance = serializer.save()
        serializer.instance.created = datetime.datetime.strptime(request.data['created'], '%Y-%m-%dT%H:%M:%S.%fZ')
        serializer.instance.modified = datetime.datetime.strptime(request.data['modified'], '%Y-%m-%dT%H:%M:%S.%fZ')
        serializer.instance.save()
        data = serializer.data

        headers = self.get_success_headers(data)
        return Response(
            data,
            status=status.HTTP_201_CREATED,
            headers=headers
        )

    def get_queryset(self):

        queryset = super(PCAGrantViewSet, self).get_queryset()
        intervention_id = self.kwargs.get('intervention_pk')
        return queryset.filter(partnership_id=intervention_id)

    def retrieve(self, request, partner_pk=None, intervention_pk=None, pk=None):
        """
        Returns a PCA Grant Object
        """
        try:
            queryset = self.queryset.get(partnership_id=intervention_pk, id=pk)
            serializer = self.serializer_class(queryset)
            data = serializer.data
        except PCAGrant.DoesNotExist:
            data = {}
        return Response(
            data,
            status=status.HTTP_200_OK
        )


class GwPCALocationViewSet(mixins.RetrieveModelMixin,
                             mixins.CreateModelMixin,
                             mixins.ListModelMixin,
                             viewsets.GenericViewSet):
    """
    Returns a list of GW Locations for an Intervention (PCA)
    """
    model = GwPCALocation
    queryset = GwPCALocation.objects.all()
    serializer_class = GWLocationSerializer
    permission_classes = (ResultChainPermission,)

    def create(self, request, *args, **kwargs):
        """
        Add an GW location to the PCA
        :return: JSON
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        serializer.instance = serializer.save()
        data = serializer.data

        headers = self.get_success_headers(data)
        return Response(
            data,
            status=status.HTTP_201_CREATED,
            headers=headers
        )

    def get_queryset(self):

        queryset = super(GwPCALocationViewSet, self).get_queryset()
        intervention_id = self.kwargs.get('intervention_pk')
        return queryset.filter(pca_id=intervention_id)

    def retrieve(self, request, partner_pk=None, intervention_pk=None, pk=None):
        """
        Returns a PCA Grant Object
        """
        try:
            queryset = self.queryset.get(pca_id=intervention_pk, id=pk)
            serializer = self.serializer_class(queryset)
            data = serializer.data
        except GwPCALocation.DoesNotExist:
            data = {}
        return Response(
            data,
            status=status.HTTP_200_OK
        )


class AmendmentLogViewSet(mixins.RetrieveModelMixin,
                             mixins.CreateModelMixin,
                             mixins.ListModelMixin,
                             viewsets.GenericViewSet):
    """
    Returns a list of Amendment logs for an Intervention (PCA)
    """
    model = AmendmentLog
    queryset = AmendmentLog.objects.all()
    serializer_class = AmendmentLogSerializer
    permission_classes = (ResultChainPermission,)

    def create(self, request, *args, **kwargs):
        """
        Add an Amendment log to the PCA
        :return: JSON
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        serializer.instance = serializer.save()
        serializer.instance.created = datetime.datetime.strptime(request.data['created'], '%Y-%m-%dT%H:%M:%S.%fZ')
        serializer.instance.modified = datetime.datetime.strptime(request.data['modified'], '%Y-%m-%dT%H:%M:%S.%fZ')
        serializer.instance.save()
        data = serializer.data

        headers = self.get_success_headers(data)
        return Response(
            data,
            status=status.HTTP_201_CREATED,
            headers=headers
        )

    def get_queryset(self):

        queryset = super(AmendmentLogViewSet, self).get_queryset()
        intervention_id = self.kwargs.get('intervention_pk')
        return queryset.filter(partnership_id=intervention_id)

    def retrieve(self, request, partner_pk=None, intervention_pk=None, pk=None):
        """
        Returns a PCA Grant Object
        """
        try:
            queryset = self.queryset.get(partnership_id=intervention_pk, id=pk)
            serializer = self.serializer_class(queryset)
            data = serializer.data
        except AmendmentLog.DoesNotExist:
            data = {}
        return Response(
            data,
            status=status.HTTP_200_OK
        )


class PartnerOrganizationsViewSet(mixins.RetrieveModelMixin,
                           mixins.ListModelMixin,
                           mixins.CreateModelMixin,
                           viewsets.GenericViewSet):
    """
    Returns a list of all Partner Organizations
    """
    queryset = PartnerOrganization.objects.all()
    serializer_class = PartnerOrganizationSerializer
    permission_classes = (PartnerPermission,)

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

    def get_queryset(self):

        queryset = super(PartnerOrganizationsViewSet, self).get_queryset()
        if not self.request.user.is_staff:
            # This must be a partner
            try:
                # TODO: Promote this to a permissions class
                current_member = PartnerStaffMember.objects.get(
                    id=self.request.user.profile.partner_staff_member
                )
            except PartnerStaffMember.DoesNotExist:
                # This is an authenticated user with no access to interventions
                return queryset.none()
            else:
                # Return all interventions this partner has
                return queryset.filter(partner=current_member.partner)
        return queryset


class PartnerStaffMembersViewSet(mixins.RetrieveModelMixin,
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


class FileTypeViewSet(mixins.RetrieveModelMixin,
                           mixins.ListModelMixin,
                           mixins.CreateModelMixin,
                           viewsets.GenericViewSet):
    """
    Returns a list of all Partner file types
    """
    queryset = FileType.objects.all()
    serializer_class = FileTypeSerializer
