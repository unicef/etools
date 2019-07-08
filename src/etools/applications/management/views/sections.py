from django.utils.translation import ugettext as _

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response


class SessionManagementView(viewsets.ViewSet):
    """Class for handling session creation, merge, split, deletion"""

    @action(detail=False, methods=['post'])
    def new(self, request, pk=None):
        data = request.data
        try:
            new_section_name = data['new_section_name']
        except KeyError:
            return Response(_('Unable to unpack'), status=status.HTTP_400_BAD_REQUEST)

        # SectionHandler.create(new_section_name, sections_to_merge)
        return Response({'success': f'{new_section_name} created'})

    @action(detail=False, methods=['post'])
    def merge(self, request, pk=None):
        data = request.data
        try:
            new_section_name = data['new_section_name']
            sections_to_merge = data['sections_to_merge']
            print('Section to Merge', sections_to_merge)
        except KeyError:
            return Response(_('Unable to unpack'), status=status.HTTP_400_BAD_REQUEST)

        sections_to_merge
        return Response({'success': f'{new_section_name} created from merge'})

    @action(detail=False, methods=['post'])
    def split(self, request, pk=None):
        data = request.data
        try:
            old_section = data['old_section']
            objects = data['objects']
            interventions = objects['interventions']
            action_point = objects['action_point']
            applied_indicators = objects['applied_indicators']
            print('Section Migrate', objects)
        except KeyError:
            return Response(_('Unable to unpack'), status=status.HTTP_400_BAD_REQUEST)

        old_section, interventions, action_point, applied_indicators
        # SectionHandler.split(new_section_name, sections_to_merge)
        return Response({'success': f'{old_section} has been split'})
