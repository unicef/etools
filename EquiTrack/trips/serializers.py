__author__ = 'jcranwellward'

from django.contrib.sites.models import Site

from rest_framework import serializers

from .models import Trip, TravelRoutes, TripFunds


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

    class Meta:
        model = TripFunds
        fields = (
            'wbs',
            'grant',
            'amount'
        )


class TripSerializer(serializers.ModelSerializer):

    traveller = serializers.CharField(source='owner')
    traveller_id = serializers.IntegerField(source='owner.id')
    supervisor_name = serializers.CharField(source='supervisor')
    section = serializers.CharField(source='section.name')
    travel_type = serializers.CharField(source='travel_type')
    # related_to_pca = serializers.CharField(source='no_pca')
    url = serializers.CharField(source='get_admin_url')
    travel_assistant = serializers.CharField(source='travel_assistant')
    security_clearance_required = serializers.CharField(source='security_clearance_required')
    ta_required = serializers.CharField(source='ta_required')
    budget_owner = serializers.CharField(source='budget_owner')
    staff_responsible_ta = serializers.CharField(source='programme_assistant')
    international_travel = serializers.CharField(source='international_travel')
    representative = serializers.CharField(source='representative')
    human_resources = serializers.CharField(source='human_resources')
    approved_by_human_resources = serializers.CharField(source='approved_by_human_resources')
    vision_approver = serializers.CharField(source='vision_approver')
    partners = serializers.CharField(source='partners')
    travel_routes = serializers.SerializerMethodField('get_TravelRoutes')
    trip_funds = serializers.SerializerMethodField('get_TripFunds')

    # pcas = serializers.CharField(source='pcas')
    # approved_by_supervisor = serializers.CharField(source='approved_by_supervisor')
    # date_supervisor_approved = serializers.DateField(source='date_supervisor_approved')
    # approved_by_budget_owner = serializers.CharField(source='approved_by_budget_owner')
    # date_budget_owner_approved = serializers.DateField(source='approved_by_budget_owner')
    # approved_by_human_resources = serializers.CharField(source='approved_by_human_resources')
    # date_human_resources_approved = serializers.DateField(source='date_supervisor_approved')
    # representative_approval = serializers.CharField(source='representative_approval')
    # date_representative_approved = serializers.DateField(source='date_representative_approved')
    # approved_date = serializers.DateField(source='date_representative_approved')
    #
    # transport_booked = serializers.CharField(source='transport_booked')
    # security_granted = serializers.CharField(source='security_granted')
    # ta_drafted = serializers.CharField(source='ta_drafted')
    # ta_drafted_date = serializers.DateField(source='ta_drafted_date')
    # ta_reference = serializers.CharField(source='ta_reference')


    def get_TravelRoutes(self, trip):
        return TripFundsSerializer(
            trip.tripfunds_set.all(),
            many=True
        ).data

    def get_TripFunds(self, trip):
        return TravelRoutesSerializer(
            trip.travelroutes_set.all(),
            many=True
        ).data

    def transform_traveller(self, obj, value):
        return obj.owner.get_full_name()

    def transform_supervisor_name(self, obj, value):
        return obj.supervisor.get_full_name()

    def transform_partners(self, obj, value):
        return ', '.join([
            partner.name for partner in obj.partners.all()
        ])

    def transform_pcas(self, obj, value):
        return ', '.join([
            pca.__unicode__() for pca in obj.pcas.all()
        ])

    def transform_url(self, obj, value):
        return 'http://{}{}'.format(
            Site.objects.get_current(),
            obj.get_admin_url()
        )

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
            'pcas',
            'travel_routes',
            'trip_funds'



        )





