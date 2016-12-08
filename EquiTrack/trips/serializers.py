__author__ = 'unicef'

#import logging

from django.contrib.sites.models import Site

from rest_framework import serializers

from .models import (
    Trip,
    TravelRoutes,
    TripFunds,
    ActionPoint,
    FileAttachment,
    TripLocation,
)


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
    wbs_name = serializers.CharField(source='wbs.name', read_only=True)
    grant_name = serializers.CharField(source='grant.name', read_only=True)

    class Meta:
        model = TripFunds
        fields = (
            'wbs',
            'wbs_name',
            'grant',
            'grant_name',
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


class ActionPointSerializer(serializers.ModelSerializer):

    id = serializers.CharField(read_only=True)
    person_responsible_name = serializers.CharField(
        source="person_responsible",
        read_only=True
    )

    class Meta:
        model = ActionPoint
        fields = (
            'id',
            'person_responsible',
            'person_responsible_name',
            'status',
            'description',
            'due_date',
            'created_date',
            'actions_taken',
            'completed_date',
            'trip',
            'comments'
        )


class FileAttachmentSerializer(serializers.ModelSerializer):

    id = serializers.CharField(read_only=True)
    file = serializers.SerializerMethodField(read_only=True)
    type_name = serializers.SerializerMethodField(read_only=True)

    def get_file(self, obj):
        return 'https://{}{}'.format(
            Site.objects.get_current(),
            obj.report.url
        )

    def get_type_name(self, obj):
        return obj.type.name

    class Meta:
        model = FileAttachment
        fields = (
            "id",
            "file",
            "type",
            "type_name",
            "caption",
            "trip",
        )


class TripSerializer(serializers.ModelSerializer):

    traveller = serializers.CharField(source='owner', read_only=True)
    traveller_id = serializers.IntegerField(source='owner.id', read_only=True)
    owner_name = serializers.CharField(source='owner', read_only=True)
    supervisor_name = serializers.CharField(source='supervisor', read_only=True)
    section_name = serializers.CharField(source='section.name', read_only=True)
    travel_type = serializers.CharField()
    url = serializers.URLField(source='get_admin_url', read_only=True)
    travel_assistant_name = serializers.CharField(source='travel_assistant', read_only=True)
    budget_owner_name = serializers.CharField(source='budget_owner', read_only=True)
    staff_responsible_ta = serializers.CharField(source='programme_assistant', read_only=True)
    representative_name = serializers.CharField(source='representative', read_only=True)
    human_resources_name = serializers.CharField(source='human_resources', read_only=True)
    vision_approver_name = serializers.CharField(source='vision_approver', read_only=True)
    office_name = serializers.CharField(source='office.name', read_only=True)

    partners = serializers.SerializerMethodField()
    partnerships = serializers.SerializerMethodField()

    travelroutes_set = TravelRoutesSerializer(many=True)
    tripfunds_set = TripFundsSerializer(many=True)
    triplocation_set = TripLocationSerializer(many=True)
    actionpoint_set = ActionPointSerializer(many=True)
    files = FileAttachmentSerializer(many=True, read_only=True)

    def get_partnerships(self, trip):
        return [pca.__unicode__() for pca in trip.pcas.all()]

    def transform_traveller(self, obj):
        return obj.owner.get_full_name()

    def transform_supervisor_name(self, obj):
        return obj.supervisor.get_full_name()

    def get_partners(self, obj):
        return [partner.name for partner in obj.partners.all()]

    def transform_url(self, obj):
        return 'https://{}{}'.format(
            Site.objects.get_current(),
            obj.get_admin_url()
        )

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
            'owner',
            'owner_name',
            'supervisor',
            'supervisor_name',
            'travel_assistant',
            'travel_assistant_name',
            'section',
            'section_name',
            'purpose_of_travel',
            'office',
            'office_name',
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
            'budget_owner_name',
            'staff_responsible_ta',
            'international_travel',
            'representative',
            'representative_name',
            'human_resources',
            'human_resources_name',
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
            'vision_approver_name',
            'partners',
            'partnerships',
            'travelroutes_set',
            'actionpoint_set',
            'tripfunds_set',
            'triplocation_set',
            'programme_assistant',
            'created_date',
            'cancelled_reason',
            'driver',
            'driver_supervisor',
            'approved_email_sent',
            'submitted_email_sent',
            'ta_trip_took_place_as_planned',
            'ta_trip_repay_travel_allowance',
            'ta_trip_final_claim',
            'pending_ta_amendment',
            'files'
        )





