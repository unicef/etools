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


def gateway_model_select(request):
    gateway_list = GatewayType.objects.all()
    return render_to_response('choices.html', {'gateway_list': gateway_list})


def all_json_models(request, gateway):
    current_gateway = GatewayType.objects.get(id=gateway)
    gs = Governorate.objects.all().filter(gateway=current_gateway)
    json_gs = serializers.serialize("json", gs)
    return HttpResponse(json_gs, mimetype="application/javascript")