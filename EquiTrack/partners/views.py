from __future__ import absolute_import

__author__ = 'jcranwellward'

from datetime import datetime
from rest_framework.generics import ListAPIView
from rest_framework.parsers import FormParser

from django.forms.models import model_to_dict

from partners.models import FACE
# from partners.exports import render_to_pdf
from locations.models import Location
from .serializers import LocationSerializer, PartnershipSerializer

from partners.models import (
    PCA,
    PCAGrant,
    PCASector,
    GwPCALocation
)


class PcaPDFView(PDFTemplateView):
    template_name = "partners/pca_pdf.html"

    def get_context_data(self, **kwargs):
        pca_id = self.kwargs.get('pca', 270)
        pca = PCA.objects.filter(id=pca_id)[0]
        pca_dict = model_to_dict(pca)
        p = pca_dict['partner']
        pca_dict['partner'] = pca.partner.name

        return super(PcaPDFView, self).get_context_data(
            pagesize="Letter",
            title="Partnership",
            pca=pca_dict,
            **kwargs
        )

# def myview(request):
#     #Retrieve data or whatever you need
#     return render_to_pdf(
#             'mytemplate.html',
#             {
#                 'pagesize':'A4',
#                 'mylist': results,
#             }
#         )

class PcaView(ListAPIView):

    model = PCA
    serializer_class = PartnershipSerializer

    def get_queryset(self):
        """
        Return locations with GPS points only
        """
        status = self.request.QUERY_PARAMS.get('status', None)
        result_structure = self.request.QUERY_PARAMS.get('result_structure', None)
        sector = self.request.QUERY_PARAMS.get('sector', None)
        gateway = self.request.QUERY_PARAMS.get('gateway', None)
        governorate = self.request.QUERY_PARAMS.get('governorate', None)
        donor = self.request.QUERY_PARAMS.get('donor', None)
        partner = self.request.QUERY_PARAMS.get('partner', None)
        district = self.request.QUERY_PARAMS.get('district', None)
        from_date = self.request.QUERY_PARAMS.get('from_date', None)
        to_date = self.request.QUERY_PARAMS.get('to_date', None)

        queryset = self.model.objects.filter(
            current=True,
        )

        if status is not None:
            queryset = self.model.objects.filter(status=status)

        if gateway is not None:
            # queryset = queryset.filter(
            #     location__gateway__id=int(gateway)
            # )
            pca_ids = GwPCALocation.objects.filter(location__gateway__id=int(gateway)).values_list('id', flat=True)
            queryset = queryset.filter(
                id__in=pca_ids
            )
        if governorate is not None:
            pca_ids = GwPCALocation.objects.filter(governorate=governorate).values_list('id', flat=True)
            queryset = queryset.filter(
                id__in=pca_ids
            )

        if district is not None:
            queryset = queryset.filter(
                region__id=int(district)
            )
        if result_structure is not None:
            queryset = queryset.filter(
                result_structure__id=int(result_structure)
            )
        if partner is not None:
            queryset = queryset.filter(
                partner__id=int(partner)
            )
        if sector is not None:
            # get the filtered pcas so far
            pcas = queryset.values_list('id', flat=True)
            # get those that contain this sector
            pcas = PCASector.objects.filter(
                pca__in=pcas,
                sector__id=int(sector)
            ).values_list('pca__id', flat=True)
            # now filter the current query by the selected ids
            queryset = queryset.filter(
                id__in=pcas
            )

        if donor is not None:
            # get the filtered pcas so far
            pcas = queryset.values_list('id', flat=True)
            # get those that contain this donor
            pcas = PCAGrant.objects.filter(
                pca__id__in=pcas,
                grant__donor__id=int(donor)
            ).values_list('pca', flat=True)
            # now filter the current query by the selected ids
            queryset = queryset.filter(
                id__in=pcas
            )

        if from_date is not None and to_date is not None:
            fdate = datetime.strptime(from_date, '%m/%d/%Y').date()
            tdate = datetime.strptime(to_date, '%m/%d/%Y').date()
            queryset = queryset.filter(
                end_date__range=(fdate, tdate)
            )

        return queryset


class LocationView(ListAPIView):

    model = GwPCALocation
    serializer_class = LocationSerializer

    def get_queryset(self):
        """
        Return locations with GPS points only
        """
        status = self.request.QUERY_PARAMS.get('status', PCA.ACTIVE)
        result_structure = self.request.QUERY_PARAMS.get('result_structure', None)
        sector = self.request.QUERY_PARAMS.get('sector', None)
        gateway = self.request.QUERY_PARAMS.get('gateway', None)
        governorate = self.request.QUERY_PARAMS.get('governorate', None)
        donor = self.request.QUERY_PARAMS.get('donor', None)
        partner = self.request.QUERY_PARAMS.get('partner', None)
        district = self.request.QUERY_PARAMS.get('district', None)

        queryset = self.model.objects.filter(
            pca__status=status,
            pca__current=True,
            location__point__isnull=False
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
