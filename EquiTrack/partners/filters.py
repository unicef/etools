__author__ = 'jcranwellward'



from django.contrib import admin
from django.db.models.query_utils import Q

from rest_framework.filters import BaseFilterBackend

from funds.models import Donor, Grant
from locations.models import (
    Governorate,
    Region,
    Locality,
    GatewayType
)
from partners.models import (
    PCA,
    PCAGrant,
    GwPCALocation,
    #IndicatorProgress,
)
from partners.serializers.serializers import PartnershipExportFilterSerializer, AgreementExportFilterSerializer, \
    InterventionExportFilterSerializer, GovernmentInterventionExportFilterSerializer
from reports.admin import SectorListFilter
from reports.models import Sector, Indicator


class PCASectorFilter(SectorListFilter):

    def queryset(self, request, queryset):

        if self.value():
            return queryset.filter(pcasector__id__contains=self.value())
        return queryset


class PCADonorFilter(admin.SimpleListFilter):

    title = 'Donor'
    parameter_name = 'donor'

    def lookups(self, request, model_admin):

        return [
            (donor.id, donor.name) for donor in Donor.objects.all()
        ]

    def queryset(self, request, queryset):

        if self.value():
            donor = Donor.objects.get(pk=self.value())
            pca_ids = PCAGrant.objects.filter(grant__donor=donor).values_list('partnership__id')
            return queryset.filter(id__in=pca_ids)
        return queryset


class PCAGrantFilter(admin.SimpleListFilter):

    title = 'Grant Number'
    parameter_name = 'grant'

    def lookups(self, request, model_admin):

        return [
            (grant.id, grant.name) for grant in Grant.objects.all()
        ]

    def queryset(self, request, queryset):

        if self.value():
            grant = Grant.objects.get(pk=self.value())
            pca_ids = PCAGrant.objects.filter(grant=grant).values_list('partnership__id')
            return queryset.filter(id__in=pca_ids)
        return queryset


class PCAGovernorateFilter(admin.SimpleListFilter):

    title = 'Governorate'
    parameter_name = 'governorate'

    def lookups(self, request, model_admin):

        return [
            (governorate.id, governorate.name) for governorate in Governorate.objects.all()
        ]

    def queryset(self, request, queryset):

        if self.value():
            governorate = Governorate.objects.get(pk=self.value())
            pca_ids = GwPCALocation.objects.filter(governorate=governorate).values_list('pca__id')
            return queryset.filter(id__in=pca_ids)
        return queryset


class PCARegionFilter(admin.SimpleListFilter):

    title = 'District'
    parameter_name = 'district'

    def lookups(self, request, model_admin):

        return [
            (region.id, region.name) for region in Region.objects.all()
        ]

    def queryset(self, request, queryset):

        if self.value():
            region = Region.objects.get(pk=self.value())
            pca_ids = GwPCALocation.objects.filter(region=region).values_list('pca__id')
            return queryset.filter(id__in=pca_ids)
        return queryset


class PCALocalityFilter(admin.SimpleListFilter):

    title = 'Sub-district'
    parameter_name = 'sub'

    def lookups(self, request, model_admin):

        return [
            (locality.id, locality.name) for locality in Locality.objects.all()
        ]

    def queryset(self, request, queryset):

        if self.value():
            locality = Locality.objects.get(pk=self.value())
            pca_ids = GwPCALocation.objects.filter(locality=locality).values_list('pca__id')
            return queryset.filter(id__in=pca_ids)
        return queryset


class PCAGatewayTypeFilter(admin.SimpleListFilter):

    title = 'Gateway'
    parameter_name = 'gateway'

    def lookups(self, request, model_admin):

        return [
            (gateway.id, gateway.name) for gateway in GatewayType.objects.all()
        ]

    def queryset(self, request, queryset):

        if self.value():
            gateway = GatewayType.objects.get(pk=self.value())
            pca_ids = GwPCALocation.objects.filter(location__gateway=gateway).values_list('pca__id')
            return queryset.filter(id__in=pca_ids)
        return queryset


class PCAIndicatorFilter(admin.SimpleListFilter):

    title = 'Indicator'
    parameter_name = 'indicator'

    def lookups(self, request, model_admin):

        return [
            (indicator.id, indicator.name) for indicator in Indicator.objects.all()
        ]

    def queryset(self, request, queryset):

        if self.value():
            pca_ids = []
            for ip in IndicatorProgress.objects.filter(indicator=self.value()):
                pca_ids.append(ip.pca.id)
            return queryset.filter(id__in=pca_ids)
        return queryset


class PCAOutputFilter(admin.SimpleListFilter):

    title = 'Output'
    parameter_name = 'output'

    def lookups(self, request, model_admin):

        return [
            (output.id, output.name) for output in Rrp5Output.objects.all()
        ]

    def queryset(self, request, queryset):

        if self.value():
            pca_ids = []
            for ip in PCASectorOutput.objects.filter(output=self.value()):
                pca_ids.append(ip.pca.id)
            return queryset.filter(id__in=pca_ids)
        return queryset


class PartnerScopeFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        if request.parser_context['kwargs']:
            return queryset.filter(partner__pk=request.parser_context['kwargs']['partner_pk'])
        return queryset


class PartnerOrganizationExportFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        parameter_serializer = PartnershipExportFilterSerializer(data=request.GET)
        parameter_serializer.is_valid(raise_exception=True)

        parameters = parameter_serializer.data

        q = Q()
        search_str = parameters.get('search')
        if search_str:
            search_q = Q(Q(name__istartswith=search_str)
                         | Q(short_name__istartswith=search_str)
                         | Q(vendor_number__istartswith=search_str))
            q &= search_q

        partner_type = parameters.get('partner_type')
        if partner_type:
            q &= Q(partner_type=partner_type)

        cso_type = parameters.get('cso_type')
        if cso_type:
            q &= Q(cso_type=cso_type)

        risk_rating = parameters.get('risk_rating')
        if risk_rating:
            q &= Q(rating=risk_rating)

        flag = parameters.get('flagged')
        if flag == PartnershipExportFilterSerializer.MARKED_FOR_DELETION:
            q &= Q(deleted_flag=True)

        show_hidden = parameters.get('show_hidden')
        if not show_hidden:
            q &= Q(hidden=False)

        return queryset.filter(q)



class AgreementExportFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        parameter_serializer = AgreementExportFilterSerializer(data=request.GET)
        parameter_serializer.is_valid(raise_exception=True)

        parameters = parameter_serializer.data

        q = Q()
        search_str = parameters.get('search')
        if search_str:
            search_q = Q(Q(partner__name__istartswith=search_str)
                         | Q(short_name__istartswith=search_str)
                         | Q(partner__vendor_number__istartswith=search_str))
            q &= search_q

        agreement_type = parameters.get('agreement_type')
        if agreement_type:
            q &= Q(agreement_type=agreement_type)

        starts_after = parameters.get('starts_after')
        if starts_after:
            q &= Q(start_date__gte=starts_after)

        ends_before = parameters.get('ends_before')
        if ends_before:
            q &= Q(end_date__lte=ends_before)

        return queryset.filter(q)


class InterventionExportFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        parameter_serializer = InterventionExportFilterSerializer(data=request.GET)
        parameter_serializer.is_valid(raise_exception=True)

        parameters = parameter_serializer.data

        q = Q()
        search_str = parameters.get('search')
        if search_str:
            search_q = Q(Q(partner__name__istartswith=search_str)
                         | Q(short_name__istartswith=search_str)
                         | Q(title__istartswith=search_str))
            q &= search_q

        document_type = parameters.get('document_type')
        if document_type:
            q &= Q(partnership_type=document_type)

        status = parameters.get('status')
        if status:
            q &= Q(status=status)

        country_programme = parameters.get('country_programme')
        if country_programme:
            q &= Q(result_structure__country_programme__name__istartswith=country_programme)

        result_structure = parameters.get('result_structure')
        if result_structure:
            q &= Q(result_structure__name__istartswith=result_structure)

        sector = parameters.get('sector')
        if sector:
            q &= Q(sectors__sector__name__istartswith=sector)

        unicef_focal_point = parameters.get('unicef_focal_point')
        if unicef_focal_point:
            q &= Q(unicef_manager__name__istartswith=unicef_focal_point)

        donor = parameters.get('donor')
        if donor:
            q &= Q(grants__grant__donor__name__istartswith=donor)

        grant = parameters.get('grant')
        if grant:
            q &= Q(grants__grant__name__istartswith=grant)

        starts_after = parameters.get('starts_after')
        if starts_after:
            q &= Q(start_date__gte=starts_after)

        ends_before = parameters.get('ends_before')
        if ends_before:
            q &= Q(ends_before__lte=ends_before)

        return queryset.filter(q)


class GovernmentInterventionExportFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        parameter_serializer = GovernmentInterventionExportFilterSerializer(data=request.GET)
        parameter_serializer.is_valid(raise_exception=True)

        parameters = parameter_serializer.data

        q = Q()
        search_str = parameters.get('search')
        if search_str:
            search_q = Q(Q(partner__name__istartswith=search_str) | Q(short_name__istartswith=search_str))
            q &= search_q

        result_structure = parameters.get('result_structure')
        if result_structure:
            q &= Q(result_structure__name__istartswith=result_structure)

        country_programme = parameters.get('country_programme')
        if country_programme:
            q &= Q(result_structure__country_programme__name__istartswith=country_programme)

        year = parameters.get('unicef_focal_point')
        if year:
            q &= Q(government__result_structure__to_date__year=year)

        return queryset.filter(q)
