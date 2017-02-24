from __future__ import unicode_literals

from rest_framework import serializers, ISO_8601


class DSASerializer(serializers.Serializer):
    start_date = serializers.DateTimeField(format=ISO_8601)
    end_date = serializers.DateTimeField(format=ISO_8601)
    daily_rate_usd = serializers.DecimalField(max_digits=20, decimal_places=4)
    night_count = serializers.IntegerField()
    amount_usd = serializers.DecimalField(max_digits=20, decimal_places=4)
    dsa_region = serializers.IntegerField()
    dsa_region_name = serializers.CharField()


class CostSummaryExpensesSerializer(serializers.Serializer):
    vendor_number = serializers.CharField(read_only=True)
    amount = serializers.DecimalField(max_digits=20, decimal_places=2, read_only=2)


class CostSummarySerializer(serializers.Serializer):
    dsa_total = serializers.DecimalField(max_digits=20, decimal_places=2, read_only=True)
    expenses_total = serializers.DecimalField(max_digits=20, decimal_places=2, read_only=True)
    deductions_total = serializers.DecimalField(max_digits=20, decimal_places=2, read_only=True)
    dsa = DSASerializer(many=True)
    preserved_expenses = serializers.DecimalField(max_digits=20, decimal_places=2, read_only=True)
    expenses_delta = serializers.DecimalField(max_digits=20, decimal_places=2, read_only=True)
    expenses = CostSummaryExpensesSerializer(many=True)
