import operator
import functools

from django.db.models import Q
from rest_framework.generics import (
    ListCreateAPIView,
    RetrieveUpdateDestroyAPIView,
)
from rest_framework.permissions import IsAdminUser

from reports.models import Result, CountryProgramme
from reports.serializers.v2 import ResultListSerializer, ResultCreateSerializer


class ResultListAPIView(ListCreateAPIView):
    queryset = Result.objects.all()
    serializer_class = ResultListSerializer
    permission_classes = (IsAdminUser,)

    def get_serializer_class(self, format=None):
        if self.request.method == "POST":
            return ResultCreateSerializer
        return super(ResultListAPIView, self).get_serializer_class()

    def get_queryset(self):
        current_cp = CountryProgramme.current()
        q = Result.objects.filter(country_programme=current_cp)

        query_params = self.request.query_params
        if query_params:
            queries = []

            if "country_programme" in query_params.keys():
                cp_year = query_params.get("country_programme")
                cp = CountryProgramme.by_year(cp_year)
                queries.append(Q(country_programme=cp))
            if "result_type" in query_params.keys():
                queries.append(Q(result_type__name=query_params.get("result_type")))

            if queries:
                expression = functools.reduce(operator.and_, queries)
                q = q.filter(expression)
        return q


class ResultDetailAPIView(RetrieveUpdateDestroyAPIView):
    queryset = Result.objects.all()
    serializer_class = ResultListSerializer
    permission_classes = (IsAdminUser,)

    def get_serializer_class(self, format=None):
        if self.request.method in ["PUT", "PATCH"]:
            return ResultCreateSerializer
        return super(ResultListAPIView, self).get_serializer_class()
