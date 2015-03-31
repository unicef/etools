__author__ = 'jcranwellward'

from django.contrib.sites.models import Site

from rest_framework import serializers

from .models import Trip


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
    approved_by_human_resources = serializers.CharField(source='approved_by_human_resources')


    def transform_traveller(self, obj, value):
        return obj.owner.get_full_name()

    def transform_supervisor_name(self, obj, value):
        return obj.supervisor.get_full_name()

    def transform_partners(self, obj, value):
        return ', '.join([
            partner.name for partner in obj.partners.all()
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
            'approved_by_human_resources'
        )

