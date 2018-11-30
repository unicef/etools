from django.db import models
from django.utils.translation import ugettext_lazy as _

from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from unicef_restlib.fields import SeparatedReadWriteField

from unicef_snapshot.serializers import SnapshotModelSerializer

from etools.applications.field_monitoring.fm_settings.serializers.cp_outputs import NestedCPOutputSerializer
from etools.applications.field_monitoring.fm_settings.serializers.methods import FMMethodTypeSerializer
from etools.applications.field_monitoring.planning.serializers import TaskListSerializer
from etools.applications.field_monitoring.fm_settings.models import LogIssue
from etools.applications.field_monitoring.shared.models import FMMethod
from etools.applications.field_monitoring.visits.models import Visit, UNICEFVisit, VisitMethodType
from etools.applications.reports.models import Result
from etools.applications.users.serializers import MinimalUserSerializer


class VisitLightSerializer(serializers.ModelSerializer):
    tasks = SeparatedReadWriteField(read_field=TaskListSerializer(many=True))
    primary_field_monitor = SeparatedReadWriteField(read_field=MinimalUserSerializer())
    team_members = SeparatedReadWriteField(read_field=MinimalUserSerializer(read_only=True))

    class Meta:
        model = Visit
        fields = (
            'id', 'reference_number', 'start_date', 'end_date', 'visit_type',
            'tasks', 'status', 'primary_field_monitor', 'team_members'
        )


class VisitListSerializer(VisitLightSerializer):
    class Meta(VisitLightSerializer.Meta):
        pass


class VisitMethodTypeSerializer(FMMethodTypeSerializer):
    class Meta(FMMethodTypeSerializer.Meta):
        model = VisitMethodType
        fields = FMMethodTypeSerializer.Meta.fields + ('is_recommended',)
        extra_kwargs = {
            'is_recommended': {'read_only': True}
        }

    def create(self, validated_data):
        validated_data['is_recommended'] = False
        return super().create(validated_data)

    def update(self, instance, validated_data):
        if instance.is_recommended:
            raise ValidationError(_('Unable to edit recommended method types'))
        return super().update(instance, validated_data)


# class VisitMethodCPOutputSerializer(NestedCPOutputSerializer):
#     def __init__(self, method_types, *args, **kwargs):
#         self.method_types = method_types
#         super().__init__(*args, **kwargs)
#
#     method_types = serializers.SerializerMethodField()
#
#     class Meta:
#         model = Result
#         fields = NestedCPOutputSerializer.Meta.fields + ('method_types',)
#
#     def get_method_types(self, obj):
#         return
#
#
# class VisitMethodSerializer(serializers.ModelSerializer):
#     def __init__(self, method_types, *args, **kwargs):
#         self.method_types = method_types
#         super().__init__(*args, **kwargs)
#
#     cp_outputs = serializers.SerializerMethodField()
#
#     class Meta:
#         model = FMMethod
#         fields = ('id', 'name', 'cp_outputs')
#
#
#     def get_scope_by_methods(self, obj):
#         methods = obj.methods.all()
#         method_types = obj.method_types.all()
#
#         return [
#             VisitMethodSerializer(filter(lambda mt: mt.method == method, method_types), method, many=True).data
#             for method in methods
#         ]
#
#     def get_cp_outputs(self, obj):
#         return [
#             VisitMethodCPOutputSerializer(filter(lambda mt: mt.cp_output == cp_output)).data
#             for cp_output in set(map(lambda ))
#         ]


class VisitSerializer(SnapshotModelSerializer,
                      VisitListSerializer):
    # method_types = VisitMethodTypeSerializer(many=True, required=False)
    specific_issues = serializers.SerializerMethodField()
    # scope_by_methods = serializers.SerializerMethodField(label=_('Scope of Site Visit By Methods'))

    class Meta(VisitListSerializer.Meta):
        fields = VisitListSerializer.Meta.fields + (
            'specific_issues',
            # 'scope_by_methods', 'method_types', 'specific_issues',
        )

    def get_specific_issues(self, obj):
        return LogIssue.objects.filter(
            models.Q(cp_output__fm_config__tasks__visits=obj.id) |
            models.Q(partner__tasks__visits=obj.id) |
            models.Q(location__tasks__visits=obj.id) |
            models.Q(location_site__tasks__visits=obj.id)
        )

    # def get_scope_by_methods(self, obj):
    #     methods = obj.methods.all()
    #     method_types = obj.method_types.all()
    #
    #     return [
    #         VisitMethodSerializer(
    #             [mt for mt in method_types if mt.method == method],
    #             method, many=True
    #         ).data
    #         for method in methods
    #     ]


class UNICEFVisitSerializer(VisitSerializer):
    class Meta(VisitSerializer.Meta):
        model = UNICEFVisit
