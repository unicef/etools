from django.db.models.fields.related_descriptors import ForwardManyToOneDescriptor, ManyToManyDescriptor
from django.db.transaction import atomic

from etools.applications.action_points.models import ActionPoint
from etools.applications.audit.models import Engagement
from etools.applications.field_monitoring.fm_settings.models import Question
from etools.applications.field_monitoring.planning.models import MonitoringActivity
from etools.applications.management.models import SectionHistory
from etools.applications.partners.models import Intervention, PartnerOrganization
from etools.applications.reports.models import AppliedIndicator, Section
from etools.applications.t2f.models import Travel
from etools.applications.tpm.models import TPMActivity, TPMVisit


class MigrationException(BaseException):
    """Exception thrown when migration is failing due validation"""


class NotDeactivatedException(MigrationException):
    """Exception thrown when an active objects is still referenced by a inactive section"""


class IndicatorSectionInconsistentException(MigrationException):
    """Exception thrown when indicator's section is not in the intervention"""


class SectionHandler:

    intervention_updatable_status = [
        Intervention.DRAFT,
        Intervention.SIGNED,
        Intervention.ACTIVE,
        Intervention.ENDED,
        Intervention.SUSPENDED
    ]
    travel_updatable_status = [
        Travel.PLANNED,
        Travel.SUBMITTED,
        Travel.REJECTED,
        Travel.APPROVED
    ]
    tpm_visit_updatable_status = [
        TPMVisit.DRAFT,
        TPMVisit.ASSIGNED,
        TPMVisit.ACCEPTED,
        TPMVisit.REJECTED,
        TPMVisit.REPORTED,
        TPMVisit.REPORT_REJECTED
    ]
    engagement_updatable_status = [
        Engagement.PARTNER_CONTACTED,
        Engagement.REPORT_SUBMITTED,
        # Engagement.FINAL,
        # Engagement.CANCELLED,
    ]
    activity_updatable_status = [
        MonitoringActivity.STATUS_DRAFT,
        MonitoringActivity.STATUS_CHECKLIST,
        MonitoringActivity.STATUS_REVIEW,
        MonitoringActivity.STATUS_ASSIGNED,
        MonitoringActivity.STATUS_DATA_COLLECTION,
    ]

    # dictionary to mark instances, for each model that has a m2m relationship to Sections,
    # in order to follow up later and clean (remove references to old sections) them.
    queryset_migration_mapping = {
        'interventions': (
            Intervention.objects.filter(status__in=intervention_updatable_status),
            'sections',
        ),
        'applied_indicators': (
            AppliedIndicator.objects.filter(lower_result__result_link__intervention__status__in=intervention_updatable_status),
            'section',
        ),
        'travels': (
            Travel.objects.filter(status__in=travel_updatable_status),
            'section',
        ),
        'engagements': (
            Engagement.objects.filter(status__in=engagement_updatable_status),
            'sections',
        ),
        'tpm_activities': (
            TPMActivity.objects.filter(tpm_visit__status__in=tpm_visit_updatable_status),
            'section',
        ),
        'action_points': (
            ActionPoint.objects.filter(status=ActionPoint.STATUS_OPEN),
            'section',
        ),
        'fm_activities': (
            MonitoringActivity.objects.filter(status__in=activity_updatable_status),
            'sections',
        ),
        'fm_questions': (
            Question.objects,
            'sections',
        ),
        'partners': (
            PartnerOrganization.objects,
            'lead_section',
        )
    }

    @staticmethod
    @atomic
    def new(new_section_name):
        """Create new section"""
        section = Section.objects.create(name=new_section_name)

        # history
        section_history = SectionHistory.objects.create(history_type=SectionHistory.CREATE)
        section_history.to_sections.set([section])
        return section

    @staticmethod
    @atomic
    def merge(new_section_name, sections_to_merge):
        """Merge two or more sections into a newly create section and migrating active objects"""
        from_instances = Section.objects.filter(pk__in=sections_to_merge)
        to_instance = Section.objects.create(name=new_section_name)
        for instance in from_instances:
            instance.active = False
            instance.name = f'{instance.name} [Inactive]'
            instance.save()
        # m2m relation need to be cleaned at the end
        m2m_to_clean = {
        }
        for from_instance in from_instances:
            m2m_to_clean = SectionHandler.__update_objects(from_instance, to_instance, m2m_to_clean)
        SectionHandler.__clean_m2m(from_instances, m2m_to_clean)

        # history
        section_history = SectionHistory.objects.create(history_type=SectionHistory.MERGE)
        section_history.from_sections.set(from_instances)
        section_history.to_sections.set([to_instance, ])

        return to_instance

    @staticmethod
    @atomic
    def close(from_instance_pk, new_section_2_new_querysets):
        """
        Close a section and split the active objects according the mapping dictionary
        new_section_2_new_querysets has a mapping of the instances to be mapped to new section
        {
            "Nutrition": {
                'interventions': [1, 3],
                'applied_indicators': [1],
                'travels': [2, 4 ],
                'tpm_activities': [],
                'action_points': [3],
                'fm_activities': [],
                'fm_questions': [],
            },
            "Health": {
                'interventions': [1, 5],
                'applied_indicators': [2],
                'travels': [4 ],
                'tpm_activities': [],
                'action_points': [1],
                'fm_activities': [],
                'fm_questions': [],
            }
        }
        """

        from_instance = Section.objects.get(pk=from_instance_pk)
        from_instance.active = False
        from_instance.name = f'{from_instance.name} [Inactive]'
        from_instance.save()

        new_sections = []
        # m2m relation need to be cleaned at the end.
        # It's a dictionary to mark instances for each model in a Many to Many Relationship
        # that we follow up for cleaning at the end of
        m2m_to_clean = {}
        for new_section_name, queryset_mapping_dict in new_section_2_new_querysets.items():
            to_instance, _ = Section.objects.get_or_create(name=new_section_name)
            new_sections.append(to_instance)
            m2m_to_clean = SectionHandler.__update_objects(from_instance, to_instance,
                                                           m2m_to_clean, queryset_mapping_dict)

        SectionHandler.__clean_m2m([from_instance], m2m_to_clean)

        # history
        section_history = SectionHistory.objects.create(history_type=SectionHistory.CLOSE)
        section_history.from_sections.set([from_instance])
        section_history.to_sections.set(new_sections)

        SectionHandler.__disabled_section_check(from_instance)
        SectionHandler.__consistent_indicators_check(new_sections)

        return new_sections

    @staticmethod
    def __update_objects(from_instance, to_instance, m2m_to_clean, section_split_dict=None):
        """
        It updates sections (from from_instance to to_instance) for all instances of all models defined in
        queryset_migration_mapping as keys, following the filters defined in that mapping.

        Params:
            from_instance: Section, instance of section to map from.
            to_instance: Section, instance of Section model that is desired to map all instances of models defined in
                        queryset_migration_mapping

            m2m_to_clean: dict, key: model, value: list of pk of objects marked for removing the to_instance Section

            section_split_dict: dict, key: name of new section, value dict with model and pk of instances to migrate
                "Nutrition": {
                    'interventions': [1, 3],
                    'applied_indicators': [1],
                    'travels': [2, 4 ],
                    'tpm_activities': [],
                    'action_points': [3],
                    'fm_activities': [],
                    'fm_questions': [],
                },
        """
        for model_key in SectionHandler.queryset_migration_mapping.keys():
            qs, section_attribute = SectionHandler.queryset_migration_mapping[model_key]

            if section_split_dict:  # if it's a close we filter the queryset
                instance_pks = section_split_dict[model_key] if section_split_dict and model_key in section_split_dict else []
                qs = qs.filter(pk__in=instance_pks)

            relation = getattr(qs.model, section_attribute)
            if isinstance(relation, ManyToManyDescriptor):
                to_update = SectionHandler.__update_m2m(qs, section_attribute, from_instance, to_instance)
                if model_key not in m2m_to_clean:
                    m2m_to_clean[model_key] = []
                m2m_to_clean[model_key].extend(to_update)

            elif isinstance(relation, ForwardManyToOneDescriptor):
                SectionHandler.__update_fk(qs, section_attribute, from_instance, to_instance)
        return m2m_to_clean

    @staticmethod
    def __update_fk(qs, section_attribute, old_section, new_section):
        """Updates qs when section is a ForeignKey"""
        qs.filter(**{section_attribute: old_section}).update(**{section_attribute: new_section})

    @staticmethod
    def __update_m2m(qs, section_attribute, old_section, new_section):
        """Updates qs when section is a ManyToManyField"""
        qs = qs.filter(**{section_attribute: old_section})
        for instance in qs:
            attr = getattr(instance, section_attribute)
            attr.add(new_section)
        return qs.values_list('pk', flat=True)

    @staticmethod
    def __clean_m2m(from_instances, m2m_to_clean):
        """
        Clean m2m fields from old sections
        NOTE: This step has to be done when the add of all section has been completed
        """
        for model_key, to_clean in m2m_to_clean.items():
            qs, section_attribute = SectionHandler.queryset_migration_mapping[model_key]
            for instance in qs.filter(pk__in=to_clean):
                attr = getattr(instance, section_attribute)
                for from_instance in from_instances:
                    attr.remove(from_instance)

    @staticmethod
    def __disabled_section_check(old_section):
        """Checks that the old section is not referenced by any active objects"""
        for _, (qs, attribute_name) in SectionHandler.queryset_migration_mapping.items():
            active_references = qs.filter(**{attribute_name: old_section})
            if active_references.exists():
                pks = ' '.join(str(pk) for pk in active_references.values_list('pk', flat=True))
                raise NotDeactivatedException(f'{qs.model.__name__} in active status exists {pks}')

    @staticmethod
    def __consistent_indicators_check(new_sections):
        """Checks that the old section is not referenced by any active objects"""
        interventions = Intervention.objects.filter(sections__in=new_sections)
        for intervention in interventions:
            applied_indicator_sections = set(AppliedIndicator.objects.filter(
                lower_result__result_link__intervention=intervention).values_list('section', flat=True).distinct())
            intervention_sections = set(intervention.sections.values_list('pk', flat=True))
            if not applied_indicator_sections.issubset(intervention_sections):
                raise IndicatorSectionInconsistentException(
                    f'Intervention {intervention.pk} has inconsistent indicators')
