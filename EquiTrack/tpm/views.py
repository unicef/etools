__author__ = 'achamseddine'

import datetime

from rest_framework import viewsets, mixins, permissions
from rest_framework.response import Response
from rest_framework import status

from .models import TPMVisit
from .serializers import TPMVisitSerializer


class TPMVisitViewSet(mixins.RetrieveModelMixin,
                            mixins.ListModelMixin,
                            mixins.CreateModelMixin,
                            mixins.UpdateModelMixin,
                            viewsets.GenericViewSet):
    """
    Returns a list of TPM Visit
    """
    model = TPMVisit
    queryset = TPMVisit.objects.all()
    serializer_class = TPMVisitSerializer
    permission_classes = (permissions.IsAdminUser,)

    def create(self, request, *args, **kwargs):
        """
        Add a TPM visit
        :return: JSON
        """

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.instance = serializer.save()

        try:
            report = request.data["report"]
        except KeyError:
            report = None

        serializer.instance.created_date = datetime.datetime.strptime(self.request.data['created_date'], '%Y-%m-%dT%H:%M:%S.%fZ')

        if report:
            serializer.instance.report = report
            serializer.instance.save()

        data = serializer.data
        headers = self.get_success_headers(data)
        return Response(
            data,
            status=status.HTTP_201_CREATED,
            headers=headers
        )

    def perform_update(self, serializer):
        instance = serializer.save()
        instance.created_date = datetime.datetime.strptime(self.request.data['created_date'], '%Y-%m-%dT%H:%M:%S.%fZ')
        instance.save()
