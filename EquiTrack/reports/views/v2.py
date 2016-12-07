from rest_framework.generics import (
    ListCreateAPIView,
    RetrieveUpdateDestroyAPIView,
)
from rest_framework.permissions import IsAdminUser

from reports.models import Result
from reports.serializers.v2 import ResultSerializer


class ResultListAPIView(ListCreateAPIView):
    queryset = Result.objects.all()
    serializer_class = ResultSerializer
    permission_classes = (IsAdminUser,)

    def get_queryset(self):
        q = Result.objects.all()
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
    serializer_class = ResultSerializer
    permission_classes = (IsAdminUser,)
