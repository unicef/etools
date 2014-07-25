__author__ = 'jcranwellward'


from rest_framework import serializers

from .models import Trip


class TripSerializer(serializers.ModelSerializer):

    traveller = serializers.CharField(source='owner')
    section = serializers.CharField(source='section.name')
    related_to_pca = serializers.CharField(source='no_pca')

    def transform_traveller(self, obj, value):
        return obj.owner.get_full_name()

    def transform_partners(self, obj, value):
        return ', '.join(obj.partners.all())

    class Meta:
        model = Trip
        fields = (
            'id',
            'traveller',
            'section',
            'purpose_of_travel',
            'from_date',
            'to_date',
            'related_to_pca',
            'partners',
        )

