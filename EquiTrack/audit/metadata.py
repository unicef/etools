from __future__ import absolute_import, division, print_function, unicode_literals

from rest_framework.metadata import SimpleMetadata

from attachments.metadata import ModelChoiceFieldMixin
from utils.common.metadata import (
    CRUActionsMetadataMixin, FSMTransitionActionMetadataMixin, ReadOnlyFieldWithChoicesMixin,
    SeparatedReadWriteFieldMetadata,)
from utils.permissions.metadata import PermissionsBasedMetadataMixin


class AuditBaseMetadata(
    ReadOnlyFieldWithChoicesMixin,
    ModelChoiceFieldMixin,
    SeparatedReadWriteFieldMetadata,
    CRUActionsMetadataMixin,
    SimpleMetadata
):

    def _update_label(self, field_name, field_info):
        if 'label' in field_info and not field_info.get('marked'):
            field_info['label'] = '+++ {} ({})'.format(field_info['label'], field_name)
            field_info['marked'] = True

        if 'child' in field_info:
            self._update_label(field_name, field_info['child'])

        if 'children' in field_info:
            for nested_field_name, field in field_info['children'].items():
                self._update_label(nested_field_name, field)

    def get_serializer_info(self, serializer):
        data = super(AuditBaseMetadata, self).get_serializer_info(serializer)
        for field_name, field_info in data.items():
            self._update_label(field_name, field_info)
        return data


class EngagementMetadata(
    FSMTransitionActionMetadataMixin,
    PermissionsBasedMetadataMixin,
    AuditBaseMetadata
):
    def get_serializer_info(self, serializer):
        if serializer.instance:
            serializer.context['instance'] = serializer.instance
        return super(EngagementMetadata, self).get_serializer_info(serializer)
