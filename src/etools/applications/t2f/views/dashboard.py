from rest_framework import mixins, viewsets
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from unicef_restlib.views import QueryStringFilterMixin

from etools.applications.t2f.models import Travel


class TravelDashboardViewSet(QueryStringFilterMixin, mixins.ListModelMixin, viewsets.GenericViewSet):
    queryset = Travel.objects.all()
    permission_classes = (IsAdminUser,)

    filters = (
        ('months', 'start_date__month__in'),
        ('year', 'start_date__year'),
        ('office_id', 'office__in'),
    )

    def list(self, request, **kwargs):
        data = {}
        travels_all = self.get_queryset()

        data["planned"] = travels_all.filter(status=Travel.PLANNED).count()
        data["approved"] = travels_all.filter(status=Travel.APPROVED).count()
        data["completed"] = travels_all.filter(status=Travel.COMPLETED).count()

        section_ids = Travel.objects.values_list('section', flat=True).distinct()
        travels_by_section = []
        for section_id in section_ids:
            travels = travels_all.filter(section=section_id)
            if travels.exists():
                planned = travels.filter(status=Travel.PLANNED).count()
                approved = travels.filter(status=Travel.APPROVED).count()
                completed = travels.filter(status=Travel.COMPLETED).count()
                section = travels.first().section
                section_trips = {
                    "section_id": section.id if section else None,
                    "section_name": section.name if section else "No Section selected",
                    "planned_travels": planned,
                    "approved_travels": approved,
                    "completed_travels": completed,
                }
                travels_by_section.append(section_trips)

        data["travels_by_section"] = travels_by_section

        return Response(data)
