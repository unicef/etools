from copy import copy

from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from django.utils.translation import gettext as _

from rest_framework import serializers
from unicef_attachments.models import Attachment, AttachmentLink
from unicef_attachments.serializers import BaseAttachmentSerializer
from unicef_locations.serializers import LocationLightSerializer
from unicef_restlib.fields import SeparatedReadWriteField
from unicef_restlib.serializers import UserContextSerializerMixin, WritableNestedSerializerMixin
from unicef_snapshot.models import Activity
from unicef_snapshot.serializers import SnapshotModelSerializer

from etools.applications.action_points.categories.models import Category
from etools.applications.action_points.categories.serializers import CategorySerializer
from etools.applications.action_points.models import ActionPoint, ActionPointComment
from etools.applications.partners.serializers.interventions_v2 import MinimalInterventionListSerializer
from etools.applications.partners.serializers.partner_organization_v2 import MinimalPartnerOrganizationListSerializer
from etools.applications.permissions2.serializers import PermissionsBasedSerializerMixin
from etools.applications.reports.serializers.v1 import ResultSerializer, SectionSerializer
from etools.applications.reports.serializers.v2 import OfficeSerializer
from etools.applications.users.serializers_v3 import MinimalUserSerializer
from etools.libraries.djangolib.utils import get_current_site


class ActionPointBaseSerializer(UserContextSerializerMixin, SnapshotModelSerializer, serializers.ModelSerializer):
    reference_number = serializers.ReadOnlyField(label=_('Reference Number'))
    author = MinimalUserSerializer(read_only=True, label=_('Author'))
    assigned_by = MinimalUserSerializer(read_only=True, label=_('Assigned By'))
    assigned_to = SeparatedReadWriteField(required=True, label=_('Assignee'),
                                          read_field=MinimalUserSerializer())

    category = SeparatedReadWriteField(label=_('Category'), required=False,
                                       read_field=CategorySerializer())

    status_date = serializers.DateTimeField(read_only=True, label=_('Status Date'))

    class Meta:
        model = ActionPoint
        fields = [
            'id', 'reference_number', 'category',
            'author', 'assigned_by', 'assigned_to',

            'high_priority', 'due_date', 'description',
            'office', 'section',
            'created', 'date_of_completion',
            'status', 'status_date',
        ]
        extra_kwargs = {
            'status': {'read_only': True},
            'date_of_completion': {'read_only': True},
            'due_date': {'required': True, 'label': _('Due On')},
        }

    def create(self, validated_data):
        validated_data.update({
            'author': self.get_user(),
            'assigned_by': self.get_user()
        })

        return super().create(validated_data)

    def update(self, instance, validated_data):
        if 'assigned_to' in validated_data:
            validated_data['assigned_by'] = self.get_user()

        return super().update(instance, validated_data)


class ActionPointListSerializer(PermissionsBasedSerializerMixin, ActionPointBaseSerializer):
    related_module = serializers.ChoiceField(label=_('Related App'), choices=ActionPoint.MODULE_CHOICES,
                                             read_only=True)

    partner = SeparatedReadWriteField(
        read_field=MinimalPartnerOrganizationListSerializer(read_only=True, label=_('Partner')),
    )
    intervention = SeparatedReadWriteField(
        read_field=MinimalInterventionListSerializer(read_only=True, label=_('PD/SPD')),
        required=False,
    )

    cp_output = SeparatedReadWriteField(
        read_field=ResultSerializer(read_only=True, label=_('CP Output')),
        required=False,
    )

    location = SeparatedReadWriteField(
        read_field=LocationLightSerializer(read_only=True, label=_('Location')),
    )

    section = SeparatedReadWriteField(
        read_field=SectionSerializer(read_only=True, label=_('Section of Assignee')),
        required=True,
    )
    office = SeparatedReadWriteField(
        read_field=OfficeSerializer(read_only=True, label=_('Office of Assignee')),
        required=True
    )

    class Meta(ActionPointBaseSerializer.Meta):
        fields = ActionPointBaseSerializer.Meta.fields + [
            'related_module', 'cp_output', 'partner', 'intervention', 'location',
            'engagement', 'psea_assessment', 'tpm_activity', 'travel_activity',
            'date_of_verification',
        ]


class ActionPointCreateSerializer(ActionPointListSerializer):
    class Meta(ActionPointListSerializer.Meta):
        pass

    def validate_category(self, value):
        if value and value.module != Category.MODULE_CHOICES.apd:
            raise serializers.ValidationError(_('Category doesn\'t belong to selected module.'))
        return value

    def create(self, validated_data):
        if 'engagement' in validated_data:
            engagement = validated_data['engagement']
            validated_data.update({
                'partner_id': engagement.partner_id,
            })
        elif 'psea_assessment' in validated_data:
            psea_assessment = validated_data['psea_assessment']
            validated_data.update({
                'partner_id': psea_assessment.partner_id
            })
        elif 'tpm_activity' in validated_data:
            activity = validated_data['tpm_activity']
            validated_data.update({
                'partner_id': activity.partner_id,
            })

        return super().create(validated_data)


class CommentSupportingDocumentSerializer(BaseAttachmentSerializer):
    class Meta(BaseAttachmentSerializer.Meta):
        extra_kwargs = copy(BaseAttachmentSerializer.Meta.extra_kwargs)
        extra_kwargs.update({
            'id': {'read_only': False},
            'file': {'read_only': True},
            'hyperlink': {'read_only': True},
        })

    def _validate_attachment(self, validated_data, instance=None):
        """file shouldn't be editable"""
        return


class CommentSerializer(UserContextSerializerMixin, WritableNestedSerializerMixin, serializers.ModelSerializer):
    user = MinimalUserSerializer(read_only=True, label=_('Author'))
    supporting_document = SeparatedReadWriteField(
        read_field=serializers.SerializerMethodField(),
        write_field=serializers.PrimaryKeyRelatedField(
            queryset=Attachment.objects.filter(object_id__isnull=True),
            allow_null=True,
        ),
        required=False
    )

    class Meta(WritableNestedSerializerMixin.Meta):
        model = ActionPointComment
        fields = (
            'id', 'user', 'comment', 'submit_date', 'supporting_document',
        )
        extra_kwargs = {
            'user': {'read_only': True},
            'submit_date': {'read_only': True},
        }

    def create(self, validated_data):
        has_supporting_document = 'supporting_document' in validated_data
        supporting_document = validated_data.pop('supporting_document', None)
        validated_data.update({
            'user': self.get_user(),
            'submit_date': timezone.now(),
            'site': get_current_site(),
        })
        instance = super().create(validated_data)
        if has_supporting_document:
            self.save_supporting_document(instance, supporting_document)
        return instance

    def update(self, instance, validated_data):
        has_supporting_document = 'supporting_document' in validated_data
        supporting_document = validated_data.pop('supporting_document', None)
        instance = super().update(instance, validated_data)
        if has_supporting_document:
            self.save_supporting_document(instance, supporting_document)
        return instance

    def get_supporting_document(self, rel):
        supporting_documents = list(rel.all())
        if not supporting_documents:
            return None

        return CommentSupportingDocumentSerializer(instance=supporting_documents[0]).data

    def save_supporting_document(self, obj, supporting_document):
        comment_ct = ContentType.objects.get_for_model(ActionPointComment)

        existing_document = list(obj.supporting_document.all())
        if existing_document:
            # unlink existing docs if there are any
            obj.supporting_document.update(object_id=None)
            AttachmentLink.objects.filter(object_id=obj.pk, content_type=comment_ct).update(object_id=None)

        if supporting_document is None:
            return

        supporting_document.content_object = obj
        supporting_document.code = 'action_points_supporting_document'
        supporting_document.uploaded_by = self.get_user()
        supporting_document.save()
        # keep attachment link in sync
        AttachmentLink.objects.get_or_create(
            attachment_id=supporting_document.pk,
            object_id=obj.pk,
            content_type=comment_ct,
        )


class HistorySerializer(serializers.ModelSerializer):
    by_user_display = serializers.ReadOnlyField(source='by_user.get_full_name', label=_('User'))
    action = serializers.SerializerMethodField(label=_('Action'))

    class Meta:
        model = Activity
        fields = ('id', 'created', 'by_user_display', 'action')
        extra_kwargs = {
            'created': {'label': _('Date')},
        }

    def get_action(self, obj):
        return ActionPoint.get_snapshot_action_display(obj)


class ActionPointSerializer(WritableNestedSerializerMixin, ActionPointListSerializer):
    comments = CommentSerializer(many=True, label=_('Actions Taken'), required=False)
    history = HistorySerializer(many=True, label=_('History'), read_only=True, source='get_meaningful_history')
    potential_verifier = MinimalUserSerializer(read_only=True, label=_('Potential Verifier'))
    verified_by = MinimalUserSerializer(read_only=True, label=_('Verified By'))

    related_object_str = serializers.ReadOnlyField(label=_('Related Document'))
    related_object_url = serializers.ReadOnlyField()

    class Meta(WritableNestedSerializerMixin.Meta, ActionPointListSerializer.Meta):
        fields = ActionPointListSerializer.Meta.fields + [
            'comments', 'history', 'related_object_str', 'related_object_url',
            'potential_verifier', 'verified_by', 'is_adequate',
        ]

    def validate_category(self, value):
        if value and value.module != self.instance.related_module:
            raise serializers.ValidationError(_('Category doesn\'t belong to selected module.'))
        return value

    def validate(self, attrs):
        validated_data = super().validate(attrs)
        if 'potential_verifier' in validated_data:
            if self.instance.author == validated_data['potential_verifier']:
                raise serializers.ValidationError(_("Author cannot verify own action point."))

        return validated_data

    def update(self, instance, validated_data):
        if 'is_adequate' in validated_data:
            validated_data['verified_by'] = self.get_user()
        return super().update(instance, validated_data)
