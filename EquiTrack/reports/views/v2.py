import operator
import functools

from django.db.models import Q
from rest_framework.generics import ListAPIView, RetrieveAPIView, DestroyAPIView
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework import status

from reports.models import Result, CountryProgramme, Indicator, LowerResult
from reports.serializers.v2 import ResultListSerializer, MinimalResultListSerializer
from reports.serializers.v1 import IndicatorSerializer
from partners.models import Intervention
from rest_framework.exceptions import ValidationError
from partners.permissions import PartneshipManagerRepPermission


class ResultListAPIView(ListAPIView):
    serializer_class = ResultListSerializer
    permission_classes = (IsAdminUser,)

    def get_serializer_class(self):
        """
        Use different serilizers for methods
        """
        if self.request.method == "GET":
            if self.request.query_params.get("verbosity", "") == 'minimal':
                return MinimalResultListSerializer
        return super(ResultListAPIView, self).get_serializer_class()

    def get_queryset(self):
        q = Result.objects.all()
        query_params = self.request.query_params
        queries = []
        result_ids = []
        if query_params:
            if "year" in query_params.keys():
                cp_year = query_params.get("year", None)
                queries.append(Q(country_programme__wbs__contains='/A0/'))
                queries.append(Q(country_programme__from_date__year__lte=cp_year))
                queries.append(Q(country_programme__to_date__year__gte=cp_year))
            if "result_type" in query_params.keys():
                queries.append(Q(result_type__name=query_params.get("result_type").title()))
            if "country_programme" in query_params.keys():
                cp = query_params.get("country_programme", None)
                queries.append(Q(country_programme=cp))
            if "values" in query_params.keys():
                result_ids = query_params.get("values", None)
                try:
                    result_ids = [int(x) for x in result_ids.split(",")]
                except ValueError:
                    raise ValidationError("Query parameter values are not integers")
                else:
                    queries.append(Q(id__in=result_ids))
        if queries:
            expression = functools.reduce(operator.and_, queries)
            q = q.filter(expression)
            # check if all value IDs passed in are returned by the query
            if result_ids and len(result_ids) != q.count():
                raise ValidationError("One of the value IDs was not found")

        if any(x in ['year', 'country_programme', 'values'] for x in query_params.keys()):
            return q
        else:
            current_cp = CountryProgramme.current()
            return q.filter(country_programme=current_cp)

    def list(self, request):
        dropdown = self.request.query_params.get("dropdown", None)
        if dropdown in ['true', 'True', '1', 'yes']:
            cp_outputs = list(self.get_queryset().values('id', 'name', 'wbs'))
            return Response(
                cp_outputs,
                status=status.HTTP_200_OK
            )
        serializer = self.get_serializer(self.get_queryset(), many=True)
        return Response(
            serializer.data,
            status=status.HTTP_200_OK
        )


class ResultDetailAPIView(RetrieveAPIView):
    queryset = Result.objects.all()
    serializer_class = ResultListSerializer
    permission_classes = (IsAdminUser,)


class ResultIndicatorListAPIView(ListAPIView):
    serializer_class = IndicatorSerializer
    permission_classes = (IsAdminUser,)

    def list(self, request, pk=None, format=None):
        """
        Return All Indicators for Result
        """
        indicators = Indicator.objects.filter(result_id=pk)
        serializer = self.get_serializer(indicators, many=True)
        return Response(
            serializer.data,
            status=status.HTTP_200_OK
        )


class LowerResultsDeleteView(DestroyAPIView):
    permission_classes = (PartneshipManagerRepPermission,)

    def delete(self, request, *args, **kwargs):
        try:
            lower_result = LowerResult.objects.get(id=int(kwargs['pk']))
        except LowerResult.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        if lower_result.result_link.intervention.status in [Intervention.DRAFT] or \
            request.user in lower_result.result_link.intervention.unicef_focal_points.all() or \
            request.user.groups.filter(name__in=['Partnership Manager',
                                                 'Senior Management Team']).exists():
            lower_result.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        else:
            raise ValidationError("You do not have permissions to delete a lower result")
