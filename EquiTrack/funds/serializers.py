from rest_framework import serializers

from .models import Donor, Grant, FundsReservationHeader


class DonorSerializer(serializers.ModelSerializer):

    id = serializers.CharField(read_only=True)

    class Meta:
        model = Donor
        fields = (
            'id',
            'name'
        )


class GrantSerializer(serializers.ModelSerializer):

    id = serializers.CharField(read_only=True)

    class Meta:
        model = Grant
        fields = (
            'id',
            'name',
            'donor'
        )


class FRHeaderSerializer(serializers.ModelSerializer):
    class Meta:
        model = FundsReservationHeader
        fields = '__all__'


class FRsSerializer(serializers.Serializer):
    frs = FRHeaderSerializer(source="*", many=True)
    total_frs_amt = serializers.SerializerMethodField()
    total_outstanding_amt = serializers.SerializerMethodField()
    total_intervention_amt = serializers.SerializerMethodField()
    total_actual_amt = serializers.SerializerMethodField()

    def get_total_frs_amt(self, obj):
        return sum([i.total_amt for i in obj.all()])

    def get_total_outstanding_amt(self, obj):
        return sum([i.outstanding_amt for i in obj.all()])

    def get_total_intervention_amt(self, obj):
        return sum([i.intervention_amt for i in obj.all()])

    def get_total_actual_amt(self, obj):
        return sum([i.actual_amt for i in obj.all()])
