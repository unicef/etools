from copy import copy
from urllib.parse import urljoin

from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.urls import reverse
from django.utils.translation import gettext as _

from rest_framework import serializers
from unicef_attachments.fields import AttachmentSingleFileField, FileTypeModelChoiceField
from unicef_attachments.models import Attachment, FileType
from unicef_attachments.serializers import AttachmentSerializerMixin
from unicef_restlib.fields import SeparatedReadWriteField

from etools.applications.action_points.serializers import ActionPointBaseSerializer, HistorySerializer
from etools.applications.audit.models import UNICEFAuditFocalPoint
from etools.applications.audit.purchase_order.models import PurchaseOrder
from etools.applications.partners.serializers.partner_organization_v2 import (
    MinimalPartnerOrganizationListSerializer,
    PartnerOrgPSEADetailsSerializer,
)
from etools.applications.permissions2.serializers import PermissionsBasedSerializerMixin
from etools.applications.psea.models import (
    Answer,
    AnswerEvidence,
    Assessment,
    AssessmentActionPoint,
    AssessmentStatusHistory,
    Assessor,
    Evidence,
    Indicator,
    Rating,
)
from etools.applications.psea.permissions import AssessmentPermissions
from etools.applications.psea.validators import EvidenceDescriptionValidator, PastDateValidator
from etools.applications.reports.serializers.v1 import SectionSerializer
from etools.applications.reports.serializers.v2 import OfficeSerializer
from etools.applications.users.serializers_v3 import MinimalUserSerializer
from etools.applications.users.validators import ExternalUserValidator


class BaseAssessmentSerializer(serializers.ModelSerializer):
    permissions = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Assessment

    def get_permissions(self, obj):
        # don't provide permissions for list view
        if self.context["view"].action == "list":
            return []

        ps = Assessment.permission_structure()
        permissions = AssessmentPermissions(
            self.context['request'].user,
            obj,
            ps,
        )
        return permissions.get_permissions()


class AssessmentSerializer(AttachmentSerializerMixin, BaseAssessmentSerializer):
    overall_rating = serializers.SerializerMethodField()
    assessor = serializers.SerializerMethodField()
    partner_name = serializers.CharField(source="partner.name", read_only=True)
    status_list = serializers.SerializerMethodField()
    rejected_comment = serializers.SerializerMethodField()
    available_actions = serializers.SerializerMethodField()
    assessment_date = serializers.DateField(
        validators=[PastDateValidator()],
        allow_null=True,
        required=False,
    )
    nfr_attachment = AttachmentSingleFileField()

    class Meta(BaseAssessmentSerializer.Meta):
        fields = '__all__'
        read_only_fields = ["reference_number", "overall_rating", "status"]

    def get_overall_rating(self, obj):
        return {
            "value": obj.overall_rating,
            "display": obj.overall_rating_display,
        }

    def get_assessor(self, obj):
        try:
            if obj.assessor.assessor_type == Assessor.TYPE_VENDOR:
                return str(obj.assessor.auditor_firm)
            else:
                return str(obj.assessor.user)
        except Assessor.DoesNotExist:
            pass
        return ""

    def get_status_list(self, obj):
        if obj.status == obj.STATUS_REJECTED:
            status_list = [
                obj.STATUS_DRAFT,
                obj.STATUS_REJECTED,
                obj.STATUS_IN_PROGRESS,
                obj.STATUS_SUBMITTED,
                obj.STATUS_FINAL,
            ]
        elif obj.status == obj.STATUS_CANCELLED:
            status_list = [
                obj.STATUS_DRAFT,
                obj.STATUS_CANCELLED,
            ]
        else:
            status_list = [
                obj.STATUS_DRAFT,
                obj.STATUS_IN_PROGRESS,
                obj.STATUS_SUBMITTED,
                obj.STATUS_FINAL,
            ]
        return [s for s in obj.STATUS_CHOICES if s[0] in status_list]

    def get_rejected_comment(self, obj):
        return obj.get_rejected_comment() or ""

    def get_available_actions(self, obj):
        # don't provide available actions for list view
        if self.context["view"].action == "list":
            return []

        ACTION_MAP = {
            Assessment.STATUS_ASSIGNED: "assign",
            Assessment.STATUS_CANCELLED: "cancel",
            Assessment.STATUS_SUBMITTED: "submit",
            Assessment.STATUS_REJECTED: "reject",
            Assessment.STATUS_FINAL: "finalize",
        }

        user = self.context['request'].user
        is_focal_group = user.groups.filter(
            name__in=[UNICEFAuditFocalPoint.name],
        ).exists()
        available_actions = []
        if is_focal_group:
            if obj.status in [obj.STATUS_DRAFT]:
                available_actions.append(ACTION_MAP.get(obj.STATUS_ASSIGNED))
            if obj.status in [obj.STATUS_SUBMITTED]:
                available_actions.append(ACTION_MAP.get(obj.STATUS_REJECTED))
                available_actions.append(ACTION_MAP.get(obj.STATUS_FINAL))
            if obj.status not in [
                    obj.STATUS_CANCELLED,
                    obj.STATUS_SUBMITTED,
                    obj.STATUS_FINAL,
            ]:
                available_actions.append(ACTION_MAP.get(obj.STATUS_CANCELLED))
        if obj.user_is_assessor(user):
            if obj.status in [obj.STATUS_IN_PROGRESS, obj.STATUS_REJECTED]:
                available_actions.append(ACTION_MAP.get(obj.STATUS_SUBMITTED))
        return available_actions


class AssessmentDetailSerializer(AssessmentSerializer):
    partner_details = PartnerOrgPSEADetailsSerializer(source="partner", read_only=True)
    focal_points_details = MinimalUserSerializer(source="focal_points", many=True, read_only=True)

    class Meta(AssessmentSerializer.Meta):
        """Same as AssessmentSerializer"""


class AssessmentExportSerializer(AssessmentSerializer):
    focal_points = serializers.SerializerMethodField()
    overall_rating_display = serializers.ReadOnlyField(label='SEA Risk Rating')
    assessment_type = serializers.ReadOnlyField(source='get_assessment_type_display')
    assessment_ingo_reason = serializers.ReadOnlyField(source='get_assessment_ingo_reason_display')

    cs1 = serializers.SerializerMethodField()
    cs2 = serializers.SerializerMethodField()
    cs3 = serializers.SerializerMethodField()
    cs4 = serializers.SerializerMethodField()
    cs5 = serializers.SerializerMethodField()
    cs6 = serializers.SerializerMethodField()

    @staticmethod
    def cs(obj, pk):
        if obj.status == Assessment.STATUS_FINAL:
            return obj.answers.get(indicator__pk=pk).rating.label

    def get_cs1(self, obj):
        return self.cs(obj, 1)

    def get_cs2(self, obj):
        return self.cs(obj, 2)

    def get_cs3(self, obj):
        return self.cs(obj, 3)

    def get_cs4(self, obj):
        return self.cs(obj, 4)

    def get_cs5(self, obj):
        return self.cs(obj, 5)

    def get_cs6(self, obj):
        return self.cs(obj, 6)

    class Meta(AssessmentSerializer.Meta):
        fields = [
            "id",
            "reference_number",
            "assessment_date",
            "partner_name",
            "status",
            "rating",
            "overall_rating_display",
            "assessment_type",
            "assessment_ingo_reason",
            "assessor",
            "focal_points",
            "cs1",
            "cs2",
            "cs3",
            "cs4",
            "cs5",
            "cs6",
        ]

    def get_focal_points(self, obj):
        return ", ".join([str(u) for u in obj.focal_points.all()])


class AssessmentDetailExportSerializer(serializers.ModelSerializer):
    # id = serializers.ReadOnlyField(source='assessment.id')
    # reference_number = serializers.ReadOnlyField(source='assessment.reference_number')
    # assessment_date = serializers.ReadOnlyField(source='assessment.assessment_date')
    partner_name = serializers.ReadOnlyField(source='assessment.partner.name')
    vendor_number = serializers.ReadOnlyField(source='assessment.partner.vendor_number')
    # status = serializers.ReadOnlyField(source='assessment.status')
    total_score = serializers.ReadOnlyField(source='assessment.rating')
    overall_rating_display = serializers.ReadOnlyField(source='assessment.overall_rating_display', label='Risk Rating')
    # assessment_type = serializers.ReadOnlyField(source='assessment.get_assessment_type_display')
    # assessment_ingo_reason = serializers.ReadOnlyField(source='assessment.get_assessment_ingo_reason_display')
    # assessor = serializers.ReadOnlyField(source='assessment.assessor')
    # focal_points = serializers.SerializerMethodField()
    # rating = serializers.ReadOnlyField(source='indicator.rating')
    cs = serializers.SerializerMethodField(label='Core standard number')
    core_standard_rating = serializers.ReadOnlyField(source='rating')
    comments = serializers.ReadOnlyField(label='Core standard comments')
    evidences = serializers.SerializerMethodField(label='Core standard proof of evidence')
    attachments = serializers.SerializerMethodField(label='Hyperlink to documents')

    class Meta(AssessmentSerializer.Meta):
        model = Answer
        fields = [
            # "id",
            # "reference_number",
            # "status",
            # "assessment_date",
            "vendor_number",
            "partner_name",
            # "overall_rating",
            "total_score",
            "overall_rating_display",
            # "assessment_type",
            # "assessment_ingo_reason",
            # "assessor",
            # "focal_points",
            "cs",
            "core_standard_rating",
            "comments",
            "evidences",
            "attachments",
        ]

    def get_cs(self, obj):
        return f'CS{obj.indicator.pk}'

    def get_focal_points(self, obj):
        return ", ".join([str(u) for u in obj.assessment.focal_points.all()])

    def get_evidences(self, obj):
        return ", ".join([str(u) for u in obj.evidences.all()])

    def get_attachments(self, obj):
        request = self.context['request']
        return ", ".join(urljoin(
            "https://{}".format(request.get_host()),
            reverse('attachments:file', kwargs={'pk': att.pk})
        ) for att in obj.attachments.all())


class AssessmentStatusSerializer(AssessmentSerializer):
    class Meta(AssessmentSerializer.Meta):
        read_only_fields = ["reference_number", "overall_rating"]

    def validate(self, data):
        data = super().validate(data)
        if self.instance and self.instance.status == data.get("status"):
            raise serializers.ValidationError(
                f"Status is already {self.instance.status}"
            )
        return data


class AssessmentStatusHistorySerializer(serializers.ModelSerializer):
    comment = serializers.CharField(required=False)

    class Meta:
        model = AssessmentStatusHistory
        fields = ["assessment", "status", "comment"]

    def validate(self, data):
        data = super().validate(data)
        if data["status"] == Assessment.STATUS_REJECTED:
            if not data.get("comment"):
                raise serializers.ValidationError(
                    _("Comment is required when rejecting."),
                )
        return data


class AssessmentActionPointSerializer(PermissionsBasedSerializerMixin, ActionPointBaseSerializer):
    reference_number = serializers.ReadOnlyField(label=_('Reference No.'))
    partner = MinimalPartnerOrganizationListSerializer(
        read_only=True,
        label=_('Related Partner'),
    )
    section = SeparatedReadWriteField(
        read_field=SectionSerializer(),
        required=True, label=_('Section of Assignee')
    )
    office = SeparatedReadWriteField(
        read_field=OfficeSerializer(),
        required=True, label=_('Office of Assignee')
    )
    is_responsible = serializers.SerializerMethodField()
    history = HistorySerializer(
        many=True,
        label=_('History'),
        read_only=True,
        source='get_meaningful_history',
    )
    url = serializers.ReadOnlyField(label=_('Link'), source='get_object_url')

    class Meta(ActionPointBaseSerializer.Meta):
        model = AssessmentActionPoint
        fields = ActionPointBaseSerializer.Meta.fields + [
            'partner',
            'section',
            'office',
            'history',
            'is_responsible',
            'url',
        ]
        fields.remove('category')
        extra_kwargs = copy(ActionPointBaseSerializer.Meta.extra_kwargs)
        extra_kwargs.update({
            'psea_assessment': {'label': _('Related Task')},
            'high_priority': {'label': _('Priority')},
        })

    def get_is_responsible(self, obj):
        return self.get_user() == obj.assigned_to

    def create(self, validated_data):
        assessment_pk = self.context[
            "request"
        ].parser_context["kwargs"].get("psea_assessment_pk")
        assessment = Assessment.objects.get(pk=assessment_pk)
        validated_data['psea_assessment'] = assessment
        validated_data.update({'partner_id': assessment.partner_id})
        return super().create(validated_data)


class AssessmentActionPointExportSerializer(serializers.Serializer):
    ref = serializers.CharField(source='reference_number')
    assigned_to = serializers.CharField(
        source='assigned_to.get_full_name',
        allow_null=True,
    )
    author = serializers.CharField(source='author.get_full_name')
    section = serializers.CharField(source='tpm_activity.section')
    status = serializers.CharField(source='get_status_display')
    due_date = serializers.DateField(format='%d/%m/%Y')
    description = serializers.CharField()


class AssessorSerializer(serializers.ModelSerializer):
    auditor_firm_name = serializers.SerializerMethodField()
    assessor_details = serializers.SerializerMethodField()
    user_details = MinimalUserSerializer(source="user", read_only=True)

    class Meta:
        model = Assessor
        fields = "__all__"
        read_only_fields = ["assessment", "assessor_details"]

    def get_assessor_details(self, obj):
        return obj.__str__()

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
    document_types = serializers.SerializerMethodField()

    class Meta:
        model = Indicator
        fields = (
            "id",
            "subject",
            "content",
            "ratings",
            "rating_instructions",
            "evidences",
            "document_types",
        )

    def get_document_types(self, obj):
        """Get document types limited to indicator"""
        MAP_INDICATOR_DOC_TYPE = {
            1: [34, 35, 54, 53],
            2: [37, 38, 39, 53],
            3: [55, 40, 41, 53],
            4: [46, 47, 53, 42, 60],
            5: [48, 56, 49, 53],
            6: [51, 52, 57, 53],
        }
        return FileType.objects.group_by("psea_answer").filter(
            pk__in=MAP_INDICATOR_DOC_TYPE.get(obj.pk, []),
        ).values(
            "id",
            "label",
        )


class AnswerAttachmentSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()
    # attachment = serializers.IntegerField(source="pk")
    file_type = FileTypeModelChoiceField(
        label=_("Document Type"),
        queryset=FileType.objects.group_by("psea_answer"),
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

    def _set_attachments(self, answer, attachment_data):
        content_type = ContentType.objects.get_for_model(Answer)
        current = list(Attachment.objects.filter(
            object_id=answer.pk,
            content_type=content_type,
        ).all())
        used = []
        for attachment in attachment_data:
            for initial in self.initial_data.get("attachments"):
                pk = initial["id"]
                current = [a for a in current if a.pk != pk]
                file_type = initial.get("file_type")
                if pk not in used and file_type == attachment["file_type"].pk:
                    attachment = Attachment.objects.filter(pk=pk).update(
                        file_type=attachment["file_type"],
                        code="psea_answer",
                        object_id=answer.pk,
                        content_type=content_type,
                    )
                    used.append(pk)
                    break
        for attachment in current:
            attachment.delete()

    def create(self, validated_data):
        evidence_data = validated_data.pop("evidences")
        attachment_data = validated_data.pop("attachments")
        with transaction.atomic():
            answer = Answer.objects.create(**validated_data)
            for evidence in evidence_data:
                AnswerEvidence.objects.create(
                    answer=answer,
                    **evidence,
                )
            self._set_attachments(answer, attachment_data)
        return answer

    def update(self, instance, validated_data):
        evidence_data = None
        if "evidences" in validated_data:
            evidence_data = validated_data.pop("evidences")
        attachment_data = None
        if "attachments" in validated_data:
            attachment_data = validated_data.pop("attachments")

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

        if attachment_data is not None:
            self._set_attachments(instance, attachment_data)
        return instance
