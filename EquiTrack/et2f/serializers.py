
from rest_framework import serializers

from .models import Travel, IteneraryItem, Expense, Deduction, CostAssignment, Clearances


class VerboseFieldRepresentationMixin(serializers.Serializer):
    use_verbose_fields = True

    @property
    def _verbose_fields(self):
        return self.use_verbose_fields

    def to_representation(self, instance):
        representation = super(VerboseFieldRepresentationMixin, self).to_representation(instance)


class IteneraryItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = IteneraryItem


class ExpenseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Expense


class DeductionSerializer(serializers.ModelSerializer):
    day_of_the_week = serializers.CharField(read_only=True)

    class Meta:
        model = Deduction


class CostAssignmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = CostAssignment


class ClearancesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Clearances


class TravelDetailsSerializer(VerboseFieldRepresentationMixin, serializers.ModelSerializer):
    itinerary = IteneraryItemSerializer(many=True)
    expenses = ExpenseSerializer(many=True)
    deductions = DeductionSerializer(many=True)
    cost_assignments = CostAssignmentSerializer(many=True)
    clearances = ClearancesSerializer()

    use_verbose_fields = True

    class Meta:
        model = Travel
        fields = ('reference_number', 'supervisor', 'office', 'end_date', 'section', 'international_travel',
                  'traveller', 'start_date', 'ta_required', 'purpose', 'id', 'itinerary', 'expenses', 'deductions',
                  'cost_assignments', 'clearances')


class TravelListSerializer(TravelDetailsSerializer):
    traveler = serializers.CharField(source='traveller.get_full_name')

    use_verbose_fields = False

    class Meta(TravelDetailsSerializer.Meta):
        fields = ('id', 'reference_number', 'traveler', 'purpose', 'start_date', 'end_date', 'status')