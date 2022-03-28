import logging

from django.db import IntegrityError
from django.utils.translation import gettext as _

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from unicef_restlib.permissions import IsSuperUser

from etools.applications.management.handlers.sections import MigrationException, SectionHandler

logger = logging.getLogger(__name__)


class SectionsManagementView(viewsets.ViewSet):
    """Class for handling session creation, merging and closing"""
    permission_classes = [IsSuperUser]

    @action(detail=False, methods=['post'])
    def new(self, request):
        try:
            new_section_name = request.data['new_section_name']
        except KeyError:
            return Response(_('Unable to unpack'), status=status.HTTP_400_BAD_REQUEST)

        try:
            section = SectionHandler.new(new_section_name)
        except (IntegrityError, MigrationException) as e:
            return Response(str(e), status=status.HTTP_400_BAD_REQUEST)

        return Response({
            'id': section.id,
            'name': section.name,
        })

    @action(detail=False, methods=['post'])
    def merge(self, request):
        try:
            new_section_name = request.data['new_section_name']
            sections_to_merge = request.data['sections_to_merge']
            logger.info('Section to Merge', sections_to_merge)
            section = SectionHandler.merge(new_section_name, sections_to_merge)
        except (KeyError, IntegrityError, MigrationException) as e:
            return Response(str(e), status=status.HTTP_400_BAD_REQUEST)

        return Response({
            'id': section.id,
            'name': section.name,
        })

    @action(detail=False, methods=['post'])
    def close(self, request):
        try:
            old_section = request.data['old_section']
            objects_dict = request.data['new_sections']
            logger.info('Section Migrate', objects_dict)
            sections = SectionHandler.close(old_section, objects_dict)
        except (KeyError, IntegrityError, MigrationException) as e:
            return Response(str(e), status=status.HTTP_400_BAD_REQUEST)

        data = [{'id': section.id, 'name': section.name} for section in sections]
        return Response(data)
