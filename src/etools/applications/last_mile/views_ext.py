from functools import cache

from django.db import connection
from django.db.models import Prefetch, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import mixins, status
from rest_framework.decorators import action
from rest_framework.filters import SearchFilter
from rest_framework.generics import GenericAPIView, ListAPIView
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet, ModelViewSet, ReadOnlyModelViewSet
from unicef_restlib.pagination import DynamicPageNumberPagination

from etools.applications.last_mile import models, serializers
from etools.applications.last_mile.permissions import IsIPLMEditor
from etools.applications.last_mile.tasks import notify_upload_waybill

def generate_csv(data):
    import csv
    import random
    n = ''.join(random.choice('abcdefghijklmnopqrstuvwxyz') for _ in range(2))
    with open(f'data_{n}.csv', 'w', newline='', encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerows(data.items())

class VisionIngestApiView(APIView):
    def post(self, request):
        print(request.data)
        generate_csv(request.data)
        return Response({}, status=status.HTTP_200_OK)


