from django.db.transaction import atomic

from etools.applications.action_points.models import ActionPoint
from etools.applications.management.models import SectionHistory
from etools.applications.partners.models import Intervention
from etools.applications.reports.models import AppliedIndicator, Section
from etools.applications.t2f.models import Travel
from etools.applications.tpm.models import TPMActivity, TPMVisit


class MigrationException(Exception):
    """Exception thrown when migration is failing due validation"""


class NotDeactivatedException(MigrationException):
    """Exception thrown when deactivated is still referenced"""


class IndicatorSectionInconsistentException(MigrationException):
    """Exception thrown when indicator's section is not in the intervention"""


class SectionHandler:

    FK = 'fk'
    M2M = 'm2m'

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

    # dictionary with info related to the model, active queryset (object relevant to the migration)
    # attribute name and type of relation
    queryset_migration_mapping = {
        'interventions': (
            Intervention.objects.filter(status__in=intervention_updatable_status),
            'sections',
            M2M
        ),
        'applied_indicators': (
            AppliedIndicator.objects.filter(lower_result__result_link__intervention__status__in=intervention_updatable_status),
            'section',
            FK
        ),
        'travels': (
            Travel.objects.filter(status__in=travel_updatable_status),
            'section',
            FK
        ),
        'tpm_activities': (
            TPMActivity.objects.filter(tpm_visit__status__in=tpm_visit_updatable_status),
            'section',
            FK
        ),
        'action_points': (
            ActionPoint.objects.filter(status=ActionPoint.STATUS_OPEN),
            'section',
            FK
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
        """Create two or more sections into a new section migrating active objects"""
        from_instances = Section.objects.filter(pk__in=sections_to_merge)
        to_instance = Section.objects.create(name=new_section_name)
        from_instances.update(active=False)

        # m2m relation need to be cleaned at the end
        m2m_to_clean = {
            'interventions': []
        }
        for from_instance in from_instances:
            SectionHandler.__update_objects(from_instance, to_instance, m2m_to_clean)
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
        """

        from_instance = Section.objects.get(pk=from_instance_pk)
        from_instance.active = False
        from_instance.save()

        new_sections = []
        # m2m relation need to be cleaned at the end
        m2m_to_clean = {
            'interventions': []
        }

        for new_section_name, queryset_mapping_dict in new_section_2_new_querysets.items():
            to_instance, _ = Section.objects.get_or_create(name=new_section_name)
            new_sections.append(to_instance)
            SectionHandler.__update_objects(from_instance, to_instance, m2m_to_clean, queryset_mapping_dict)

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
        update eTools queryset from one instance to another
        section_split_dict has the redistribution mapping after a section is closed
        """
        for model_key in SectionHandler.queryset_migration_mapping.keys():
            qs, section_attribute, relation = SectionHandler.queryset_migration_mapping[model_key]

            if section_split_dict:  # if it's a close we filter the queryset
                instance_pks = section_split_dict[model_key] if section_split_dict else []
                qs = qs.filter(pk__in=instance_pks)

            if relation == SectionHandler.M2M:
                to_update = SectionHandler.__update_m2m(qs, section_attribute, from_instance, to_instance)
                m2m_to_clean[model_key].extend(to_update)

            elif relation == SectionHandler.FK:
                SectionHandler.__update_fk(qs, section_attribute, from_instance, to_instance)

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
            qs, section_attribute, relation = SectionHandler.queryset_migration_mapping[model_key]
            for instance in qs.filter(pk__in=to_clean):
                attr = getattr(instance, section_attribute)
                for from_instance in from_instances:
                    attr.remove(from_instance)

    @staticmethod
    def __disabled_section_check(old_section):
        """Checks that the old section is not referenced by any active objects"""
        for _, (qs, attribute_name, _) in SectionHandler.queryset_migration_mapping.items():
            if qs.filter(**{attribute_name: old_section}).exists():
                raise NotDeactivatedException(f'{qs.model.__name__} in active status exists')

    @staticmethod
    def __consistent_indicators_check(new_sections):
        """Checks that the old section is not referenced by any active objects"""
        interventions = Intervention.objects.filter(sections__in=new_sections)
        for intervention in interventions:
            applied_indicator_sections = set(AppliedIndicator.objects.filter(
                lower_result__result_link__intervention=intervention).values_list('section', flat=True).distinct())
            intervention_sections = set(intervention.sections.values_list('pk', flat=True))
            if not applied_indicator_sections.issubset(intervention_sections):
                raise IndicatorSectionInconsistentException(f'Intervention {intervention.pk} has inconsistent indicators')
