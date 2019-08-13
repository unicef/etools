from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from rest_framework import serializers

from etools.applications.psea.models import Assessment, Assessor, Evidence, Indicator, Rating


class AssessmentSerializer(serializers.ModelSerializer):
    rating = serializers.SerializerMethodField()

    class Meta:
        model = Assessment
        fields = '__all__'
        read_only_fields = ["reference_number"]

    def get_rating(self, obj):
        return obj.rating()

    def create(self, validated_data):
        if "assessment_date" not in validated_data:
            validated_data["assessment_date"] = timezone.now().date()
        return super().create(validated_data)


class AssessorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Assessor
        fields = "__all__"

    def validate(self, data):
        """Ensure correct assessor setup based on assessor type

        EXTERNAL - requires user
        UNICEF - requires user
        VENDOR - requires auditor_firm and order_number
        """
        assessor_type = data.get("assessor_type")
        if assessor_type in [Assessor.TYPE_EXTERNAL, Assessor.TYPE_UNICEF]:
            if not data.get("user"):
                raise serializers.ValidationError(_("User is required."))
            # ensure to clear data
            data["auditor_firm"] = None
            data["auditor_firm_staff"] = []
            data["order_number"] = ""
        elif assessor_type == Assessor.TYPE_VENDOR:
            if not data.get("auditor_firm"):
                raise serializers.validationError(
                    _("Auditor Firm is required."),
                )
            if not data.get("order_number"):
                raise serializers.validationError(
                    _("PO Number is required."),
                )
            # ensure to clear data
            data["user"] = None
        return data


class ActiveListSerializer(serializers.ListSerializer):
    def to_representation(self, data):
        data = data.filter(active=True)
        return super().to_representation(data)


class EvidenceSerializer(serializers.ModelSerializer):
    class Meta:
        list_serializer_class = ActiveListSerializer
        model = Evidence
        fields = ("id", "label", "requires_description")


class RatingSerializer(serializers.ModelSerializer):
    class Meta:
        list_serializer_class = ActiveListSerializer
        model = Rating
        fields = ("id", "label", "weight")


class IndicatorSerializer(serializers.ModelSerializer):
    evidences = EvidenceSerializer(many=True, read_only=True)
    ratings = RatingSerializer(
        many=True,
        read_only=True,
    )

    class Meta:
        model = Indicator
        fields = ("id", "subject", "content", "ratings", "evidences")
