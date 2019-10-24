from copy import copy

from django.utils.translation import ugettext_lazy as _

from rest_framework import serializers
from unicef_attachments.fields import FileTypeModelChoiceField
from unicef_attachments.models import Attachment, FileType
from unicef_restlib.fields import SeparatedReadWriteField

from etools.applications.action_points.serializers import ActionPointBaseSerializer, HistorySerializer
from etools.applications.partners.serializers.partner_organization_v2 import MinimalPartnerOrganizationListSerializer
from etools.applications.permissions2.serializers import PermissionsBasedSerializerMixin
from etools.applications.reports.serializers.v1 import SectionSerializer
from etools.applications.travel.models import ActivityActionPoint, Itinerary, ItineraryStatusHistory
from etools.applications.travel.permissions import ItineraryPermissions
from etools.applications.users.serializers import OfficeSerializer


class BaseItinerarySerializer(serializers.ModelSerializer):
    permissions = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Itinerary

    def get_permissions(self, obj):
        # don't provide permissions for list view
        if self.context["view"].action == "list":
            return []

        ps = Itinerary.permission_structure()
        permissions = ItineraryPermissions(
            self.context['request'].user,
            obj,
            ps,
        )
        return permissions.get_permissions()


class ItineraryAttachmentSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()
    file_type = FileTypeModelChoiceField(
        label=_("Document Type"),
        queryset=FileType.objects.filter(code="travel_docs"),
    )

    class Meta:
        model = Attachment
        fields = ("id", "url", "file_type", "created")

    def update(self, instance, validated_data):
        validated_data["code"] = "travel_docs"
        return super().update(instance, validated_data)

    def get_url(self, obj):
        if obj.file:
            url = obj.file.url
            request = self.context.get("request", None)
            if request is not None:
                return request.build_absolute_uri(url)
            return url
        return ""


class ItinerarySerializer(BaseItinerarySerializer):
    attachments = ItineraryAttachmentSerializer(many=True, required=False)
    status_list = serializers.SerializerMethodField()
    rejected_comment = serializers.SerializerMethodField()
    available_actions = serializers.SerializerMethodField()

    class Meta(BaseItinerarySerializer.Meta):
        fields = '__all__'
        read_only_fields = ["reference_number", "status"]

    def get_status_list(self, obj):
        if obj.status == obj.STATUS_REJECTED:
            status_list = [
                obj.STATUS_DRAFT,
                obj.STATUS_REJECTED,
                obj.STATUS_SUBMISSION_REVIEW,
                obj.STATUS_SUBMITTED,
                obj.STATUS_APPROVED,
                obj.STATUS_REVIEW,
                obj.STATUS_COMPLETED,
            ]
        elif obj.status == obj.STATUS_CANCELLED:
            status_list = [
                obj.STATUS_DRAFT,
                obj.STATUS_SUBMISSION_REVIEW,
                obj.STATUS_CANCELLED,
            ]
        else:
            status_list = [
                obj.STATUS_DRAFT,
                obj.STATUS_SUBMISSION_REVIEW,
                obj.STATUS_SUBMITTED,
                obj.STATUS_APPROVED,
                obj.STATUS_REVIEW,
                obj.STATUS_COMPLETED,
            ]
        return [s for s in obj.STATUS_CHOICES if s[0] in status_list]

    def get_rejected_comment(self, obj):
        return obj.get_rejected_comment() or ""

    def get_available_actions(self, obj):
        # don't provide available actions for list view
        if self.context["view"].action == "list":
            return []

        ACTION_MAP = {
            Itinerary.STATUS_DRAFT: "revise",
            Itinerary.STATUS_SUBMISSION_REVIEW: "subreview",
            Itinerary.STATUS_CANCELLED: "cancel",
            Itinerary.STATUS_SUBMITTED: "submit",
            Itinerary.STATUS_REJECTED: "reject",
            Itinerary.STATUS_APPROVED: "approve",
            Itinerary.STATUS_REVIEW: "review",
            Itinerary.STATUS_COMPLETED: "complete",
        }

        user = self.context['request'].user
        available_actions = []
        if user == obj.traveller:
            if obj.status in [obj.STATUS_DRAFT]:
                available_actions.append(
                    ACTION_MAP.get(obj.STATUS_SUBMISSION_REVIEW),
                )
            if obj.status in [obj.STATUS_SUBMISSION_REVIEW]:
                available_actions.append(ACTION_MAP.get(obj.STATUS_DRAFT))
                available_actions.append(ACTION_MAP.get(obj.STATUS_SUBMITTED))
            if obj.status in [obj.STATUS_APPROVED]:
                available_actions.append(ACTION_MAP.get(obj.STATUS_REVIEW))
            if obj.status in [obj.STATUS_APPROVED, obj.STATUS_REVIEW]:
                available_actions.append(ACTION_MAP.get(obj.STATUS_COMPLETED))
            if obj.status in [obj.STATUS_REJECTED]:
                available_actions.append(ACTION_MAP.get(obj.STATUS_DRAFT))
            if obj.status not in [
                    obj.STATUS_CANCELLED,
                    obj.STATUS_SUBMITTED,
                    obj.STATUS_REVIEW,
                    obj.STATUS_COMPLETED,
            ]:
                available_actions.append(ACTION_MAP.get(obj.STATUS_CANCELLED))
        if user == obj.supervisor:
            if obj.status in [obj.STATUS_SUBMITTED]:
                available_actions.append(ACTION_MAP.get(obj.STATUS_APPROVED))
                available_actions.append(ACTION_MAP.get(obj.STATUS_REJECTED))
        return available_actions


class ItineraryExportSerializer(ItinerarySerializer):
    itinerary_items = serializers.SerializerMethodField()
    activities = serializers.SerializerMethodField()

    class Meta(ItinerarySerializer.Meta):
        fields = [
            "id",
            "reference_number",
            "status",
            "supervisor",
            "description",
            "start_date",
            "end_date",
            "traveller",
            "itinerary_items",
            "activities",
        ]

    def get_itinerary_items(self, obj):
        return ", ".join([str(a) for a in obj.items.all()])

    def get_activities(self, obj):
        return ", ".join([str(a) for a in obj.activities.all()])


class ItineraryStatusSerializer(ItinerarySerializer):
    class Meta(ItinerarySerializer.Meta):
        read_only_fields = ["reference_number"]

    def validate(self, data):
        data = super().validate(data)
        if self.instance and self.instance.status == data.get("status"):
            raise serializers.ValidationError(
                f"Status is already {self.instance.status}"
            )
        return data


class ItineraryStatusHistorySerializer(serializers.ModelSerializer):
    comment = serializers.CharField(required=False)

    class Meta:
        model = ItineraryStatusHistory
        fields = ["itinerary", "status", "comment"]

    def validate(self, data):
        data = super().validate(data)
        if data["status"] == Itinerary.STATUS_REJECTED:
            if not data.get("comment"):
                raise serializers.ValidationError(
                    _("Comment is required when rejecting."),
                )
        return data


class ActivityActionPointSerializer(
        PermissionsBasedSerializerMixin,
        ActionPointBaseSerializer,
):
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
        model = ActivityActionPoint
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
            'travel': {'label': _('Related Task')},
            'high_priority': {'label': _('Priority')},
        })

    def get_is_responsible(self, obj):
        return self.get_user() == obj.assigned_to

    def create(self, validated_data):
        itinerary_pk = self.context[
            "request"
        ].parser_context["kwargs"].get("travel_pk")
        itinerary = Itinerary.objects.get(pk=itinerary_pk)
        validated_data['travel'] = itinerary
        validated_data.update({'partner_id': itinerary.partner_id})
        return super().create(validated_data)


class ActivityActionPointExportSerializer(serializers.Serializer):
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


class ReportAttachmentSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()
    file_type = FileTypeModelChoiceField(
        label=_("Document Type"),
        queryset=FileType.objects.filter(code="travel_report_docs"),
    )

    class Meta:
        model = Attachment
        fields = ("id", "url", "file_type", "created")

    def update(self, instance, validated_data):
        validated_data["code"] = "travel_docs"
        return super().update(instance, validated_data)

    def get_url(self, obj):
        if obj.file:
            url = obj.file.url
            request = self.context.get("request", None)
            if request is not None:
                return request.build_absolute_uri(url)
            return url
        return ""


class ReportSerializer(serializers.ModelSerializer):
    attachments = ReportAttachmentSerializer(many=True, required=False)

    class Meta:
        fields = '__all__'
        read_only_fields = ["itinerary"]
