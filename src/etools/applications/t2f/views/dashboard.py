
from rest_framework import mixins, viewsets
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response

from etools.applications.t2f.models import ActionPoint, Travel


class TravelDashboardViewSet(mixins.ListModelMixin,
                             viewsets.GenericViewSet):
    queryset = Travel.objects.all()
    permission_classes = (IsAdminUser,)

    def list(self, request, **kwargs):
        data = {}
        months = request.query_params.get("months", None)
        if months is not None:
            months = map(lambda x: int(x), months.split(','))
        year = request.query_params.get("year", None)
        office_id = request.query_params.get("office_id", None)
        try:
            travels_all = Travel.objects.filter(
                start_date__year=year,
                start_date__month__in=months,
            )
        except ValueError:
            travels_all = Travel.objects.filter(
                start_date__year=year,
            )

        if office_id:
            travels_all = travels_all.filter(office_id=office_id)

        data["planned"] = travels_all.filter(status=Travel.PLANNED).count()
        data["approved"] = travels_all.filter(status=Travel.APPROVED).count()
        data["completed"] = travels_all.filter(status=Travel.COMPLETED).count()

        section_ids = Travel.objects.all().values_list('section', flat=True).distinct()
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


class ActionPointDashboardViewSet(mixins.ListModelMixin,
                                  viewsets.GenericViewSet):
    queryset = ActionPoint.objects.all()
    permission_classes = (IsAdminUser,)

    def list(self, request, **kwargs):
        data = {}
        office_id = request.query_params.get("office_id", None)
        if office_id:
            office_id = office_id.split(',')
        section_ids = Travel.objects.all().values_list('section', flat=True).distinct()
        action_points_by_section = []
        for section_id in section_ids:
            travels = Travel.objects.filter(section=section_id)
            if office_id:
                travels = travels.filter(office_id__in=office_id)
            if travels.exists():
                action_points = ActionPoint.objects.filter(travel__in=travels)
                total = action_points.count()
                completed = action_points.filter(status=Travel.COMPLETED).count()
                section = travels.first().section
                section_action_points = {
                    "section_id": section.id if section else None,
                    "section_name": section.name if section else "No Section selected",
                    "total_action_points": total,
                    "completed_action_points": completed,
                }
                action_points_by_section.append(section_action_points)

        data["action_points_by_section"] = action_points_by_section

        return Response(data)
