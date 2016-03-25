__author__ = 'jcranwellward'

#import logging

from django.contrib.sites.models import Site

from rest_framework import serializers

from .models import Trip, TravelRoutes, TripFunds, ActionPoint, FileAttachment, TripLocation


class TravelRoutesSerializer(serializers.ModelSerializer):

    class Meta:
        model = TravelRoutes
        fields = (
            'origin',
            'destination',
            'depart',
            'arrive',
            'remarks'
        )


class TripFundsSerializer(serializers.ModelSerializer):
    wbs = serializers.CharField(source='wbs.name')
    grant = serializers.CharField(source='grant.name')

    class Meta:
        model = TripFunds
        fields = (
            'wbs',
            'grant',
            'amount'
        )


class TripFunds2Serializer(serializers.ModelSerializer):

    class Meta:
        model = TripFunds
        fields = (
            'wbs',
            'grant',
            'amount'
        )


class TripLocationSerializer(serializers.ModelSerializer):

    class Meta:
        model = TripLocation
        fields = (
            'governorate',
            'region',
            'locality',
            'location'
        )


class ActionPoint2Serializer(serializers.ModelSerializer):

    class Meta:
        model = ActionPoint
        fields = (
            'id',
            'person_responsible',
            'status',
            'description',
            'due_date',
            'comments',
            'created_date',
            'actions_taken',
            'completed_date'
        )
        extra_kwargs = {'id': {'read_only': False}}


class ActionPointSerializer(serializers.ModelSerializer):


    person_responsible_name = serializers.CharField(source="person_responsible",
                                                    read_only=True)

    class Meta:
        model = ActionPoint
        fields = (
            'id',
            'person_responsible',
            'person_responsible_name',
            'status',
            'description',
            'due_date',
            'comments'
        )
        extra_kwargs = {'id': {'read_only': False}}


class FileAttachmentSerializer(serializers.ModelSerializer):

    id = serializers.CharField(read_only=True)

    class Meta:
        model = FileAttachment
        fields = (
            "id",
            "report",
            "type",
            "object_id",
            "content_type",
            "trip",
        )


class Trip2Serializer(serializers.ModelSerializer):

    partners = serializers.SerializerMethodField()
    pcas = serializers.SerializerMethodField()

    travelroutes_set = TravelRoutesSerializer(many=True)
    tripfunds_set = TripFunds2Serializer(many=True)
    triplocation_set = TripLocationSerializer(many=True)
    actionpoint_set = ActionPoint2Serializer(many=True)

    def get_pcas(self, trip):
        return [pca.id for pca in trip.pcas.all()]

    def get_partners(self, obj):
        return [partner.id for partner in obj.partners.all()]

    def create(self, validated_data):

        try:
            travel_routes = validated_data.pop('travelroutes_set')
        except KeyError:
            travel_routes = []

        try:
            tripfunds = validated_data.pop('tripfunds_set')
        except KeyError:
            tripfunds = []

        try:
            triplocations = validated_data.pop('triplocation_set')
        except KeyError:
            triplocations = []

        try:
            tripactions = validated_data.pop('actionpoint_set')
        except KeyError:
            tripactions = []

        try:
            trip = Trip.objects.create(**validated_data)

            for travel in travel_routes:
                TravelRoutes.objects.create(trip=trip, **travel)

            for fund in tripfunds:
                TripFunds.objects.create(trip=trip, **fund)

            for location in triplocations:
                TripLocation.objects.create(trip=trip, **location)

            for action in tripactions:
                ActionPoint.objects.create(trip=trip, **action)

        except Exception as ex:
            raise serializers.ValidationError({'instance': ex.message})

        return trip

    def update(self, instance, validated_data):
        instance.save()

        return instance

    class Meta:
        model = Trip
        fields = (
            'id',
            # 'url',
            'owner',
            # 'owner_id',
            'supervisor',
            # 'supervisor_name',
            'travel_assistant',
            'section',
            'purpose_of_travel',
            'office',
            'main_observations',
            'constraints',
            'lessons_learned',
            'opportunities',
            'travel_type',
            'from_date',
            'to_date',
            'status',
            'security_clearance_required',
            'ta_required',
            'budget_owner',
            # 'staff_responsible_ta',
            'international_travel',
            'representative',
            'human_resources',
            'approved_by_supervisor',
            'date_supervisor_approved',
            'approved_by_budget_owner',
            'date_budget_owner_approved',
            'approved_by_human_resources',
            'date_human_resources_approved',
            'representative_approval',
            'date_representative_approved',
            'approved_date',
            'transport_booked',
            'security_granted',
            'ta_drafted',
            'ta_drafted_date',
            'ta_reference',
            'vision_approver',
            'partners',
            'pcas',
            'travelroutes_set',
            'actionpoint_set',
            'tripfunds_set',
            'triplocation_set',
            # 'all_files'
        )


class TripSerializer(serializers.ModelSerializer):

    traveller = serializers.CharField(source='owner')
    traveller_id = serializers.IntegerField(source='owner.id')
    supervisor_name = serializers.CharField(source='supervisor')
    section = serializers.CharField(source='section.name')
    travel_type = serializers.CharField()
    # related_to_pca = serializers.CharField(source='no_pca')
    url = serializers.URLField(source='get_admin_url')
    travel_assistant = serializers.CharField()
    budget_owner = serializers.CharField()
    staff_responsible_ta = serializers.CharField(source='programme_assistant')
    representative = serializers.CharField()
    human_resources = serializers.CharField()
    vision_approver = serializers.CharField()
    partners = serializers.SerializerMethodField()
    travel_routes = serializers.SerializerMethodField()
    actionpoint_set = ActionPointSerializer(many=True)
    all_files = FileAttachmentSerializer(many=True)
    trip_funds = serializers.SerializerMethodField()
    partnerships = serializers.SerializerMethodField()
    office = serializers.CharField(source='office.name')

    def get_travel_routes(self, trip):
        return TravelRoutesSerializer(
            trip.travelroutes_set.all(),
            many=True
        ).data

    def get_trip_funds(self, trip):
        return TripFundsSerializer(
            trip.tripfunds_set.all(),
            many=True
        ).data

    def get_partnerships(self, trip):
        return [pca.__unicode__() for pca in trip.pcas.all()]

    def transform_traveller(self, obj):
        return obj.owner.get_full_name()

    def transform_supervisor_name(self, obj):
        return obj.supervisor.get_full_name()

    def get_partners(self, obj):
        return [partner.name for partner in obj.partners.all()]

    def transform_url(self, obj):
        return 'http://{}{}'.format(
            Site.objects.get_current(),
            obj.get_admin_url()
        )

    def update(self, instance, validated_data):
        """
        docs: http://www.django-rest-framework.org/api-guide/serializers/#writable-nested-representations

        :param instance:
        :param validated_data:
        :return:
        """

        try:
            aps_data = validated_data.pop('actionpoint_set')
        except KeyError:
            aps_data = []

        for key, value in validated_data.iteritems():
            setattr(instance, key, value)

        instance.save()

        if aps_data:
            existing_ap_ids = [obj.id for obj in instance.actionpoint_set.all()]
            for ap_data in aps_data:

                if ap_data.get('id') and ap_data['id'] in existing_ap_ids:
                    ap_id = ap_data["id"]
                    # remove the id from the field to avoid errors
                    del ap_data["id"]
                    # update current action point with ap_data
                    ActionPoint.objects.filter(pk=ap_id).update(**ap_data)

                else:
                    #create a new action_point
                    ActionPoint.objects.create(trip=instance, **ap_data)

        return instance

    class Meta:
        model = Trip
        fields = (
            'id',
            'url',
            'traveller',
            'traveller_id',
            'supervisor',
            'supervisor_name',
            'travel_assistant',
            'section',
            'purpose_of_travel',
            'office',
            'main_observations',
            'constraints',
            'lessons_learned',
            'opportunities',
            'travel_type',
            'from_date',
            'to_date',
            # 'related_to_pca',
            'partners',
            'status',
            'security_clearance_required',
            'ta_required',
            'budget_owner',
            'staff_responsible_ta',
            'international_travel',
            'representative',
            'human_resources',
            'approved_by_supervisor',
            'date_supervisor_approved',
            'approved_by_budget_owner',
            'date_budget_owner_approved',
            'approved_by_human_resources',
            'date_human_resources_approved',
            'representative_approval',
            'date_representative_approved',
            'approved_date',
            'transport_booked',
            'security_granted',
            'ta_drafted',
            'ta_drafted_date',
            'ta_reference',
            'vision_approver',
            'partners',
            'partnerships',
            'travel_routes',
            'actionpoint_set',
            'trip_funds',
            'all_files',




        )





