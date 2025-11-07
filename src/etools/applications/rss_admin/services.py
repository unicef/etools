from typing import Iterable, Tuple

from etools_validator.exceptions import TransitionError

from etools.applications.partners.models import Intervention, PartnerOrganization
from etools.applications.organizations.models import Organization
from etools.applications.audit.serializers.engagement import (
    AuditSerializer,
    MicroAssessmentSerializer,
    SpecialAuditSerializer,
    SpotCheckSerializer,
    StaffSpotCheckSerializer,
)
from etools.applications.audit.models import Engagement
from etools.applications.field_monitoring.data_collection.models import (
    ActivityOverallFinding,
    ActivityQuestion,
    ActivityQuestionOverallFinding,
)
from etools.applications.partners.validation.interventions import transition_to_closed


class ProgrammeDocumentService:

    @staticmethod
    def bulk_close(interventions: Iterable[Intervention]) -> dict:
        """Close PDs in bulk.

        Accepts an iterable of Intervention instances and attempts to close each one
        according to the same business rules used elsewhere. Returns a dict with
        'closed_ids' and 'errors' arrays, preserving the existing API contract.
        """
        result = {
            'closed_ids': [],
            'errors': [],  # legacy per-item list of errors with id and errors
        }

        for intervention in interventions:
            # Only allow closing from ENDED status
            if intervention.status != Intervention.ENDED:
                result['errors'].append({'id': intervention.id, 'errors': ['PD is not in ENDED status']})
                continue
            try:
                transition_to_closed(intervention)
                intervention.status = Intervention.CLOSED
                intervention.save()
                result['closed_ids'].append(intervention.id)
            except TransitionError as exc:
                # TransitionError from validators may be a list-like message; normalize to list of strings
                message = str(exc)
                # Some validators raise with a list inside; DRF usually stringifies to "['msg']". Keep as string.
                result['errors'].append({'id': intervention.id, 'errors': [message] if not isinstance(message, list) else message})

        # Group errors by error message to reduce payload size for many IDs
        if result['errors']:
            grouped = {}
            for item in result['errors']:
                err_list = item.get('errors') or []
                # take the first error text as the grouping key for simplicity
                key = err_list[0] if err_list else 'Unknown error'
                if key not in grouped:
                    grouped[key] = []
                grouped[key].append(item['id'])
            result['grouped_errors'] = [{'message': k, 'ids': v} for k, v in grouped.items()]

        return result


class PartnerService:
    @staticmethod
    def map_partner_to_workspace(
        *, vendor_number: str, lead_office=None, lead_section=None
    ) -> Tuple[PartnerOrganization, bool]:
        """Ensure a `PartnerOrganization` exists for the given vendor number in this tenant.

        Optionally updates `lead_office` and `lead_section` if provided.

        Returns the PartnerOrganization instance and a boolean indicating creation.
        """
        org = Organization.objects.get(vendor_number=vendor_number)
        partner, created = PartnerOrganization.objects.get_or_create(organization=org)

        updates = {}
        if lead_office is not None:
            updates['lead_office'] = lead_office
        if lead_section is not None:
            updates['lead_section'] = lead_section

        if updates:
            for field_name, value in updates.items():
                setattr(partner, field_name, value)
            partner.save(update_fields=list(updates.keys()))

        return partner, created


class EngagementService:
    @staticmethod
    def execute_action(
        *, engagement, action: str, send_back_comment: str | None = None, cancel_comment: str | None = None
    ) -> Engagement:
        """Execute a state transition on an engagement and persist it.

        Permissions are enforced by transition decorators on the model.
        """
        if hasattr(engagement, 'get_subclass'):
            engagement = engagement.get_subclass()

        if action == 'submit':
            engagement.submit()
        elif action == 'send_back':
            engagement.send_back(send_back_comment)
        elif action == 'cancel':
            engagement.cancel(cancel_comment)
        elif action == 'finalize':
            engagement.finalize()

        engagement.save()
        return engagement

    TYPE_SERIALIZERS = {
        Engagement.TYPES.audit: AuditSerializer,
        Engagement.TYPES.ma: MicroAssessmentSerializer,
        Engagement.TYPES.sa: SpecialAuditSerializer,
        Engagement.TYPES.sc: SpotCheckSerializer,  # default for sc
    }

    @classmethod
    def serializer_for_instance(cls, obj):
        if hasattr(obj, 'get_subclass'):
            obj = obj.get_subclass()

        etype = getattr(obj, 'engagement_type', None)
        if etype == Engagement.TYPES.sc and getattr(getattr(obj, 'agreement', None), 'auditor_firm', None):
            if getattr(obj.agreement.auditor_firm, 'unicef_users_allowed', False):
                return StaffSpotCheckSerializer
        return cls.TYPE_SERIALIZERS.get(etype)

    @staticmethod
    def attach_files(*, engagement, engagement_file=None, report_file=None):
        """Attach uploaded files to the engagement with normalized codes."""
        if hasattr(engagement, 'get_subclass'):
            engagement = engagement.get_subclass()

        if engagement_file:
            if getattr(engagement_file, 'code', None) != 'audit_engagement':
                engagement_file.code = 'audit_engagement'
                engagement_file.save(update_fields=['code'])
            engagement.engagement_attachments.add(engagement_file)

        if report_file:
            if getattr(report_file, 'code', None) != 'audit_report':
                report_file.code = 'audit_report'
                report_file.save(update_fields=['code'])
            engagement.report_attachments.add(report_file)

        return engagement


class FieldMonitoringService:
    @staticmethod
    def save_hact_answer(*, activity, partner, value):
        aq = ActivityQuestion.objects.filter(
            monitoring_activity=activity,
            is_hact=True,
            partner=partner,
            is_enabled=True,
        ).first()
        if not aq:
            return None

        aq_of, _ = ActivityQuestionOverallFinding.objects.get_or_create(activity_question=aq)
        aq_of.value = value
        aq_of.save()

        if activity.status == activity.STATUSES.completed and activity.end_date:
            partner.update_programmatic_visits(event_date=activity.end_date, update_one=True)

        return aq_of

    @staticmethod
    def set_on_track(*, activity, partner, on_track: bool):
        aof, _ = ActivityOverallFinding.objects.get_or_create(
            monitoring_activity=activity,
            partner=partner,
        )
        aof.on_track = on_track
        aof.save()
        return aof
