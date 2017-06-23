from rest_framework.filters import BaseFilterBackend

from .models import Engagement


class DisplayStatusFilter(BaseFilterBackend):
    """
    Filter engagements by display status instead of database status value.
    """

    def filter_queryset(self, request, queryset, view):
        status = request.query_params.get('status')
        if not status:
            return queryset

        if status in [
            Engagement.STATUSES.report_submitted,
            Engagement.STATUSES.final,
            Engagement.STATUSES.canceled
        ]:
            return queryset.filter(status=status)

        partner_contacted = queryset.filter(status=Engagement.STATUSES.partner_contacted)
        if status == Engagement.DISPLAY_STATUSES.partner_contacted:
            return partner_contacted.filter(
                date_of_field_visit__isnull=True
            )
        elif status == Engagement.DISPLAY_STATUSES.field_visit:
            return partner_contacted.filter(
                date_of_field_visit__isnull=False, date_of_draft_report_to_ip__isnull=True
            )
        elif status == Engagement.DISPLAY_STATUSES.draft_issued_to_partner:
            return partner_contacted.filter(
                date_of_draft_report_to_ip__isnull=False, date_of_comments_by_ip__isnull=True
            )
        elif status == Engagement.DISPLAY_STATUSES.draft_issued_to_unicef:
            return partner_contacted.filter(
                date_of_draft_report_to_unicef__isnull=False, date_of_comments_by_unicef__isnull=True
            )
        elif status == Engagement.DISPLAY_STATUSES.comments_received_by_unicef:
            return partner_contacted.filter(
                date_of_comments_by_unicef__isnull=False
            )

        return queryset
