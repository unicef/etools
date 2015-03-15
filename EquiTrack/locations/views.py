__author__ = 'unicef-leb-inn'

from locations.models import GatewayType, Governorate, CartoDBTable
from django.shortcuts import render_to_response
from django.http import HttpResponse
from django.core import serializers

from rest_framework import status
from rest_framework.response import Response
from rest_framework.generics import ListAPIView
from rest_framework.parsers import FormParser
from rest_framework.renderers import JSONPRenderer


class CartoDBTablesView(ListAPIView):
    model = CartoDBTable
