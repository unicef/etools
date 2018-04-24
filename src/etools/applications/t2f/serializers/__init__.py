
from rest_framework import ISO_8601, serializers

from etools.applications.publics.models import TravelExpenseType


class DSASerializer(serializers.Serializer):
    start_date = serializers.DateTimeField(format=ISO_8601)
    end_date = serializers.DateTimeField(format=ISO_8601)
    daily_rate = serializers.DecimalField(max_digits=20, decimal_places=4)
    night_count = serializers.IntegerField()
    total_amount = serializers.DecimalField(max_digits=20, decimal_places=4)
    paid_to_traveler = serializers.DecimalField(max_digits=20, decimal_places=4)
    deduction = serializers.DecimalField(max_digits=20, decimal_places=4)
    dsa_region = serializers.IntegerField()
    dsa_region_name = serializers.CharField()


class CostSummaryExpensesSerializer(serializers.Serializer):
    vendor_number = serializers.CharField(read_only=True)
    amount = serializers.DecimalField(max_digits=20, decimal_places=2, read_only=2)
    label = serializers.CharField(read_only=True)
    currency = serializers.PrimaryKeyRelatedField(read_only=True)

    def to_representation(self, instance):
        data = super(CostSummaryExpensesSerializer, self).to_representation(instance)
        if data['vendor_number'] == TravelExpenseType.USER_VENDOR_NUMBER_PLACEHOLDER:
            data['vendor_number'] = 'Traveler'
        return data


class ExpensesTotalSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=20, decimal_places=2, read_only=True)
    currency = serializers.PrimaryKeyRelatedField(read_only=True)


class CostSummarySerializer(serializers.Serializer):
    dsa_total = serializers.DecimalField(max_digits=20, decimal_places=2, read_only=True)
    expenses_total = ExpensesTotalSerializer(many=True)
    deductions_total = serializers.DecimalField(max_digits=20, decimal_places=2, read_only=True)
    paid_to_traveler = serializers.DecimalField(max_digits=20, decimal_places=2, read_only=True)
    dsa = DSASerializer(many=True)
    preserved_expenses = serializers.DecimalField(max_digits=20, decimal_places=2, read_only=True)
    expenses_delta = serializers.DecimalField(max_digits=20, decimal_places=2, read_only=True)
    expenses = CostSummaryExpensesSerializer(many=True)
