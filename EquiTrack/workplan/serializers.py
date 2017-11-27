from django.contrib.auth import get_user_model

from rest_framework import serializers

from locations.models import Location
from partners.models import PartnerOrganization
from users.models import Section
from workplan.models import (
    Label, ResultWorkplanProperty, Workplan, WorkplanProject,)


class WorkplanSerializer(serializers.ModelSerializer):
    class Meta:
        model = Workplan
        fields = ('id', 'status', 'country_programme', 'workplan_projects')


class LabelSerializer(serializers.ModelSerializer):
    class Meta:
        model = Label
        fields = '__all__'


class ResultWorkplanPropertySerializer(serializers.ModelSerializer):

    sections = serializers.PrimaryKeyRelatedField(
        many=True,
        read_only=False,
        queryset=Section.objects.all()
    )
    geotag = serializers.PrimaryKeyRelatedField(
        many=True,
        read_only=False,
        queryset=Location.objects.all()
    )
    partners = serializers.PrimaryKeyRelatedField(
        many=True,
        read_only=False,
        queryset=PartnerOrganization.objects.all()
    )
    responsible_persons = serializers.PrimaryKeyRelatedField(
        many=True,
        read_only=False,
        queryset=get_user_model().objects.all()
    )

    class Meta:
        model = ResultWorkplanProperty
        fields = '__all__'


class WorkplanProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkplanProject
        fields = '__all__'
