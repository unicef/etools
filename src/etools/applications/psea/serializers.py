from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from rest_framework import serializers
from unicef_attachments.fields import FileTypeModelChoiceField
from unicef_attachments.models import Attachment, FileType

from etools.applications.audit.purchase_order.models import PurchaseOrder
from etools.applications.psea.models import Answer, AnswerEvidence, Assessment, Assessor, Evidence, Indicator, Rating
from etools.applications.psea.permissions import AssessmentPermissions
from etools.applications.psea.validation import AssessmentValid
from etools.applications.psea.validators import EvidenceDescriptionValidator
from etools.applications.users.validators import ExternalUserValidator


class BaseAssessmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Assessment

    def get_permissions(self, obj):
        if isinstance(self.instance, list):
            return []

        ps = Assessment.permission_structure()
        permissions = AssessmentPermissions(
            self.context['request'].user,
            self.instance,
            ps,
        )
        return permissions.get_permissions()

    def validate(self, data):
        data = super().validate(data)
        if self.context.get('skip_global_validator', None):
            return data
        focal_points = None
        if "focal_points" in data:
            focal_points = data.pop("focal_points")
        validator = AssessmentValid(
            data,
            old=self.instance,
            user=self.context['request'].user,
        )

        if not validator.is_valid:
            raise serializers.ValidationError({'errors': validator.errors})
        if focal_points is not None:
            data["focal_points"] = focal_points
        return data


class AssessmentSerializer(BaseAssessmentSerializer):
    rating = serializers.SerializerMethodField()
    permissions = serializers.SerializerMethodField(read_only=True)
    assessor = serializers.SerializerMethodField()

    class Meta(BaseAssessmentSerializer.Meta):
        fields = '__all__'
        read_only_fields = ["reference_number", "overall_rating"]

    def get_rating(self, obj):
        return obj.rating()

    def get_assessor(self, obj):
        try:
            if obj.assessor.assessor_type == Assessor.TYPE_VENDOR:
                return str(obj.assessor.auditor_firm)
            else:
                return str(obj.assessor.user)
        except Assessor.DoesNotExist:
            pass
        return ""

    def create(self, validated_data):
        if "assessment_date" not in validated_data:
            validated_data["assessment_date"] = timezone.now().date()
        focal_points = None
        if "focal_points" in validated_data:
            focal_points = validated_data.pop("focal_points")
        instance = super().create(validated_data)
        if focal_points is not None:
            instance.focal_points.set(focal_points)
        return instance


class AssessmentStatusSerializer(BaseAssessmentSerializer):
    comment = serializers.CharField(required=False)

    class Meta(BaseAssessmentSerializer.Meta):
        fields = ["status", "comment"]

    def validate(self, data):
        data = super().validate(data)
        if data["status"] == Assessment.STATUS_IN_PROGRESS:
            previous_status = self.instance.status_history.first()
            if previous_status.status == Assessment.STATUS_SUBMITTED:
                if not data.get("comment"):
                    raise serializers.ValidationError(
                        _("Comment is required when rejecting."),
                    )
        return data


class AssessorSerializer(serializers.ModelSerializer):
    auditor_firm_name = serializers.SerializerMethodField()

    class Meta:
        model = Assessor
        fields = "__all__"
        read_only_fields = ["assessment"]

    def get_auditor_firm_name(self, obj):
        if obj.auditor_firm:
            return obj.auditor_firm.name
        return ""

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
            if assessor_type == Assessor.TYPE_EXTERNAL:
                validate = ExternalUserValidator()
                validate(data["user"].email)
            else:
                if not data["user"].email.endswith("@unicef.org"):
                    raise serializers.ValidationError(
                        _("User does not have UNICEF email address."),
                    )
            # ensure to clear data
            data["auditor_firm"] = None
            data["auditor_firm_staff"] = []
            data["order_number"] = ""
        elif assessor_type == Assessor.TYPE_VENDOR:
            if not data.get("auditor_firm"):
                raise serializers.ValidationError(
                    _("Auditor Firm is required."),
                )
            if not data.get("order_number"):
                raise serializers.ValidationError(
                    _("PO Number is required."),
                )
            # ensure we have a valid order number that exists
            # for firm
            if not PurchaseOrder.objects.filter(
                    auditor_firm=data.get("auditor_firm"),
                    order_number=data.get("order_number"),
            ).exists():
                raise serializers.ValidationError(
                    _("PO Number is invalid."),
                )
            # ensure to clear data
            data["user"] = None
        return data

    def create(self, validated_data):
        validated_data["assessment_id"] = self.context["view"].kwargs.get(
            "nested_1_pk",
        )
        return super().create(validated_data)


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


class AnswerAttachmentSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()
    # attachment = serializers.IntegerField(source="pk")
    file_type = FileTypeModelChoiceField(
        label=_("Document Type"),
        queryset=FileType.objects.filter(code="psea_answer"),
    )

    class Meta:
        model = Attachment
        fields = ("id", "url", "file_type", "created")

    def update(self, instance, validated_data):
        validated_data["code"] = "psea_answer"
        return super().update(instance, validated_data)

    def get_url(self, obj):
        if obj.file:
            url = obj.file.url
            request = self.context.get("request", None)
            if request is not None:
                return request.build_absolute_uri(url)
            return url
        return ""


class AnswerEvidenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnswerEvidence
        fields = ("id", "evidence", "description")
        validators = [EvidenceDescriptionValidator()]


class AnswerSerializer(serializers.ModelSerializer):
    attachments = AnswerAttachmentSerializer(many=True, required=False)
    evidences = AnswerEvidenceSerializer(many=True)

    class Meta:
        model = Answer
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if hasattr(self, "initial_data"):
            self.initial_data["assessment"] = self._context.get(
                "request"
            ).parser_context["kwargs"].get("nested_1_pk")

    def create(self, validated_data):
        evidence_data = validated_data.pop("evidences")
        attachment_data = validated_data.pop("attachments")
        answer = Answer.objects.create(**validated_data)
        for evidence in evidence_data:
            AnswerEvidence.objects.create(
                answer=answer,
                **evidence,
            )
        content_type = ContentType.objects.get_for_model(Answer)
        used = []
        for attachment in attachment_data:
            for initial in self.initial_data.get("attachments"):
                pk = initial["id"]
                file_type = initial["file_type"]
                if pk not in used and file_type == attachment["file_type"].pk:
                    Attachment.objects.filter(pk=pk).update(
                        file_type=attachment["file_type"],
                        code="psea_answer",
                        object_id=answer.pk,
                        content_type=content_type,
                    )
                    used.append(pk)
                    break
        return answer

    def update(self, instance, validated_data):
        evidence_data = None
        if "evidences" in validated_data:
            evidence_data = validated_data.pop("evidences")

        instance.rating = validated_data.get("rating", instance.rating)
        instance.comments = validated_data.get("comments", instance.comments)
        instance.save()

        if evidence_data is not None:
            evidence_current = list(instance.evidences.all())
            for data in evidence_data:
                answer_evidence, created = AnswerEvidence.objects.update_or_create(
                    answer=instance,
                    evidence=data.get("evidence"),
                    defaults={
                        "description": data.get("description"),
                    }
                )
                if not created:
                    evidence_current.remove(answer_evidence)
            # delete obsolete answer evidences
            for evidence in evidence_current:
                evidence.delete()

        return instance
