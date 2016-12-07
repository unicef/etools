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

            if "partner_type" in query_params.keys():
                queries.append(Q(partner_type=query_params.get("partner_type")))
            if "cso_type" in query_params.keys():
                queries.append(Q(cso_type=query_params.get("cso_type")))
            if "hidden" in query_params.keys():
                queries.append(Q(cso_type=query_params.get("cso_type")))

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
