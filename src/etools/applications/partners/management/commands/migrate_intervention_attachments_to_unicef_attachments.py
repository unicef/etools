import logging

from django.contrib.contenttypes.models import ContentType
from django.core.management import BaseCommand
from django.db import connection

from unicef_attachments.models import Attachment, FileType as AttachmentFileType

from etools.applications.partners.models import FileType, Intervention, InterventionAttachment
from etools.applications.users.models import Country
from etools.libraries.tenant_support.utils import run_on_all_tenants

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Migrate legacy intervention file types to unicef_attachments file types'

    def add_arguments(self, parser):
        parser.add_argument('--schema', dest='schema')

    def migrate_file_types(self):
        logger.info('Migrating file types for schema %s' % connection.schema_name)
        file_types_mapping_abstract = {
            'FACE': 'face',
            'Progress Report': 'progress_report',
            '(Legacy) Final Partnership Review': 'final_partnership_review',
            'Correspondence': 'correspondence',
            'Supply/Distribution Plan': 'supply_plan',
            'Data Processing Agreement': 'data_processing_agreement',
            'Activities involving children and young people': 'activities_involving_children',
            'Special Conditions for Construction Works': 'special_conditions_for_constriction',
            'Other': 'other',
        }
        file_types_mapping = {}

        for old_ft_name, new_file_type_name in file_types_mapping_abstract.items():
            try:
                old_file_type = FileType.objects.get(name=old_ft_name)
            except FileType.DoesNotExist:
                raise RuntimeError(f'Unable to find partners.FileType for "{old_ft_name}". '
                                   f'Run `init-partner-file-type` management command first.')

            try:
                new_file_type = AttachmentFileType.objects.get(code='pmp_documents', name=new_file_type_name)
            except AttachmentFileType.DoesNotExist:
                raise RuntimeError(f'Unable to find unicef_attachments.FileType for "{old_ft_name}". '
                                   f'Load `attachments_file_types` fixture first.')

            file_types_mapping[old_file_type] = new_file_type

        attachments_to_update = []
        for intervention_attachment in InterventionAttachment.objects.all():
            attachment = intervention_attachment.attachment_file.first()
            if not attachment:
                continue

            attachment.file_type_id = file_types_mapping[intervention_attachment.type].id
            attachments_to_update.append(attachment)

        Attachment.objects.bulk_update(attachments_to_update, fields=['file_type_id'])

    def migrate_documents(self):
        logger.info('Copying attachments from InterventionAttachment to Intervention '
                    'for schema %s' % connection.schema_name)

        intervention_ct = ContentType.objects.get_for_model(Intervention)
        intervention_attachment_ct = ContentType.objects.get_for_model(InterventionAttachment)
        attachments = []
        for intervention_id in Intervention.objects.values_list('id', flat=True):
            is_active_map = {}
            for intervention_attachment in InterventionAttachment.objects.filter(intervention_id=intervention_id):
                attachment = intervention_attachment.attachment_file.first()
                if not attachment:
                    logger.info(f'No unicef_attachment object linked to '
                                f'InterventionAttachment {intervention_attachment.pk}')
                    continue

                is_active_map[attachment.pk] = intervention_attachment.active

            intervention_attachments = list(
                Attachment.objects.filter(
                    code='partners_intervention_attachment',
                    content_type=intervention_attachment_ct,
                    object_id__in=InterventionAttachment.objects.filter(
                        intervention_id=intervention_id
                    ).values_list('id', flat=True),
                )
            )

            for attachment in intervention_attachments:
                attachment.is_active = is_active_map[attachment.pk]
                attachment.pk = None
                attachment.id = None
                attachment.code = 'partners_intervention_attachments'
                attachment.content_type = intervention_ct
                attachment.object_id = intervention_id

            attachments.extend(intervention_attachments)

        objs = Attachment.objects.bulk_create(attachments)
        logger.info(f'Created {len(objs)} attachments')

    def handle(self, *args, **options):

        logger.info('Command started')

        countries = Country.objects.exclude(name__iexact='global')
        if options['schema']:
            country = countries.get(schema_name=options['schema'])
            connection.set_tenant(country)
            self.migrate_file_types()
            self.migrate_documents()
        else:
            run_on_all_tenants(self.migrate_file_types)
            run_on_all_tenants(self.migrate_documents)

        logger.info('Command finished')
