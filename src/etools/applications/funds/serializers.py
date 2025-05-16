
from rest_framework import serializers

from etools.applications.funds.models import (
    Donor,
    FundsCommitmentHeader,
    FundsCommitmentItem,
    FundsReservationHeader,
    FundsReservationItem,
    Grant,
)


class FRLineItemSerializer(serializers.ModelSerializer):
    value = serializers.DecimalField(source='overall_amount_dc', decimal_places=2, max_digits=20)

    class Meta:
        model = FundsReservationItem
        fields = ('donor',
                  'donor_code',
                  'line_item',
                  'grant_number',
                  'fund',
                  'wbs',
                  'value')


class FRHeaderSerializer(serializers.ModelSerializer):
    line_item_details = FRLineItemSerializer(source='fr_items', read_only=True, many=True)

    class Meta:
        model = FundsReservationHeader
        fields = '__all__'


class FRsSerializer(serializers.Serializer):
    frs = FRHeaderSerializer(source="*", many=True)
    total_frs_amt = serializers.SerializerMethodField()
    total_outstanding_amt = serializers.SerializerMethodField()
    total_intervention_amt = serializers.SerializerMethodField()
    total_actual_amt = serializers.SerializerMethodField()
    earliest_start_date = serializers.SerializerMethodField()
    latest_end_date = serializers.SerializerMethodField()
    currencies_match = serializers.SerializerMethodField()
    multi_curr_flag = serializers.SerializerMethodField()

    def all_fr_currencies_match(self, obj):
        all_currencies = [i.currency for i in obj.all()]
        return len(set(all_currencies)) == 1

    def get_earliest_start_date(self, obj):
        seq = [i.start_date for i in obj.all()]
        return min(seq) if seq else None

    def get_latest_end_date(self, obj):
        seq = [i.end_date for i in obj.all()]
        return max(seq) if seq else None

    def get_total_frs_amt(self, obj):
        return sum([i.total_amt_local for i in obj.all()]) if self.all_fr_currencies_match(obj) else 0

    def get_total_outstanding_amt(self, obj):
        return sum([i.outstanding_amt for i in obj.all()]) if self.all_fr_currencies_match(obj) else 0

    def get_total_intervention_amt(self, obj):
        return sum([i.intervention_amt for i in obj.all()]) if self.all_fr_currencies_match(obj) else 0

    def get_total_actual_amt(self, obj):
        return sum([i.actual_amt_local for i in obj.all()]) if self.all_fr_currencies_match(obj) else 0

    def get_currencies_match(self, obj):
        return self.all_fr_currencies_match(obj)

    def get_multi_curr_flag(self, obj):
        for i in obj.all():
            if i.multi_curr_flag:
                return True
        return False


class FundsReservationItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = FundsReservationItem
        fields = "__all__"


class FundsCommitmentHeaderSerializer(serializers.ModelSerializer):
    class Meta:
        model = FundsCommitmentHeader
        fields = "__all__"


class FundsCommitmentItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = FundsCommitmentItem
        fields = "__all__"


class GrantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Grant
        fields = "__all__"


class DonorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Donor
        fields = "__all__"


class ExternalFundsReservationItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = FundsReservationItem
        exclude = ('id', 'created', 'modified', 'fund_reservation')


class ExternalFundsReservationSerializer(serializers.ModelSerializer):
    business_area_code = serializers.CharField(required=True, allow_null=False, allow_blank=False)
    fr_items = ExternalFundsReservationItemSerializer(many=True, required=True, allow_null=False)
    pd_reference_number = serializers.CharField(required=True, allow_null=False, allow_blank=False)

    class Meta:
        model = FundsReservationHeader
        exclude = ('id', 'created', 'modified', 'intervention')

    def create(self, validated_data):
        validated_data.pop('business_area_code')
        validated_data.pop('pd_reference_number')
        fr_items = validated_data.pop('fr_items', None)
        instance = super().create(validated_data)
        to_create = [FundsReservationItem(fund_reservation=instance, **fr_item) for fr_item in fr_items]
        FundsReservationItem.objects.bulk_create(to_create)
        return instance
