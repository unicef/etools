__author__ = 'jcranwellward'


from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.generics import ListAPIView
from rest_framework.parsers import FormParser
from rest_framework.renderers import JSONPRenderer

from partners.models import FACE
from .serializers import GWLocationSerializer, RapidProRequest

from partners.models import (
    PCA,
    GwPCALocation
)


class PartnersView(ListAPIView):
    model = PCA
    renderer_classes = (JSONPRenderer,)


class LocationView(ListAPIView):

    model = GwPCALocation
    serializer_class = GWLocationSerializer

    def get_queryset(self):
        """
        Return locations with GPS points only
        """
        return self.model.objects.filter(
            pca__status=PCA.ACTIVE,
            location__point__isnull=False
        )


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
