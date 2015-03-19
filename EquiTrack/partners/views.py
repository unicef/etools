__author__ = 'jcranwellward'


from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.generics import ListAPIView
from rest_framework.parsers import FormParser

from partners.models import FACE
from locations.models import Location
from .serializers import LocationSerializer, RapidProRequest

from partners.models import (
    PCA,
    PCAGrant,
    PCASector,
    GwPCALocation
)


class LocationView(ListAPIView):

    model = GwPCALocation
    serializer_class = LocationSerializer

    def get_queryset(self):
        """
        Return locations with GPS points only
        """
        status = self.request.DATA.get('status', PCA.ACTIVE)
        result_structure = self.request.DATA.get('result_structure', None)
        sector = self.request.DATA.get('sector', None)
        gateway = self.request.DATA.get('gateway', None)
        governorate = self.request.DATA.get('governorate', None)
        donor = self.request.DATA.get('donor', None)
        partner = self.request.DATA.get('partner', None)
        district = self.request.DATA.get('district', None)

        queryset = self.model.objects.filter(
            pca__status=status,
            location__point__isnull=False
        )

        if gateway is not None:
            queryset = queryset.filter(
                gateway__id=gateway
            )
        if governorate is not None:
            queryset = queryset.filter(
                governorate__id=governorate
            )
        if district is not None:
            queryset = queryset.filter(
                district__id=district
            )
        if result_structure is not None:
            queryset = queryset.filter(
                pca__result_structure__id=result_structure
            )
        if partner is not None:
            queryset = queryset.filter(
                pca__partner__id=partner
            )
        if sector is not None:
            # get the filtered pcas so far
            pcas = queryset.values_list('pca', flat=True)
            # get those that contain this sector
            pcas = PCASector.objects.filter(
                pca__id__in=pcas,
                sector__id=sector
            ).values_list('pca', flat=True)
            # now filter the current query by the selected ids
            queryset = queryset.filter(
                pca__id=pcas
            )

        if donor is not None:
            # get the filtered pcas so far
            pcas = queryset.values_list('pca', flat=True)
            # get those that contain this donor
            pcas = PCAGrant.objects.filter(
                pca__id__in=pcas,
                donor__id=donor
            ).values_list('pca', flat=True)
            # now filter the current query by the selected ids
            queryset = queryset.filter(
                pca__id=pcas
            )

        pca_locs = queryset.values_list('location', flat=True)
        locs = Location.objects.filter(
            id__in=pca_locs
        )
        return locs


class RapidProWebHookMixin(object):

    authentication_classes = ()
    parser_classes = (FormParser,)

    def get_data(self, request):
        return RapidProRequest(data=request.DATA)


class ValidatePCANumberView(RapidProWebHookMixin, APIView):

    def post(self, request):
        data = self.get_data(request)
        if data.is_valid():
            valid = PCA.objects.filter(
                number=data.object['text'],
                status=PCA.ACTIVE,
                partner__phone_number=data.object['phone']).exists()
            return Response({'valid': 'valid' if valid else 'invalid'},
                            status=status.HTTP_200_OK)
        return Response(data.errors, status=status.HTTP_400_BAD_REQUEST)


class CreateFACERequestView(RapidProWebHookMixin, APIView):

    def post(self, request):
        data = self.get_data(request)
        if data.is_valid():
            if data.object['values']:
                pca_number = amount = None
                for val in data.object['values']:
                    if val["label"] == "pca_number":
                        pca_number = val['text']
                    if val["label"] == "amount":
                        amount = val['text']
                if pca_number and amount:
                    pca = PCA.objects.filter(
                        number=pca_number,
                        status=PCA.ACTIVE,
                        partner__phone_number=data.object['phone']
                    ).order_by('-amendment_number').first()
                    if pca:
                        face = FACE.objects.create(
                            ref='{}-{}'.format(pca.number, amount),
                            amount=amount,
                            pca=pca,
                        )
                        return Response({'faceref': face.ref},
                                        status=status.HTTP_200_OK)
        return Response(data.errors, status=status.HTTP_400_BAD_REQUEST)
