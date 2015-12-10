__author__ = 'jcranwellward'

from django.contrib import admin

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
    PCASector,
    GwPCALocation,
    IndicatorProgress,
    PCASectorOutput
)
from reports.admin import SectorListFilter
from reports.models import Sector, Indicator, Rrp5Output


class PCASectorFilter(SectorListFilter):

    def queryset(self, request, queryset):

        if self.value():
            sector = Sector.objects.get(pk=self.value())
            pca_ids = PCASector.objects.filter(sector=sector).values_list('pca_id')
            return queryset.filter(id__in=pca_ids)
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