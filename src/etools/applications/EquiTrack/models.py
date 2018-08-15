from django.db.models import Aggregate


class DSum(Aggregate):
    function = 'SUM'
    template = '%(function)s(DISTINCT %(expressions)s)'
    name = 'Sum'
