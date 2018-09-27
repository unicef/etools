from django.db.models import Aggregate, CharField, Value


class StringConcat(Aggregate):
    """ A custom aggregation function that returns "," separated strings """

    function = 'GROUP_CONCAT'
    template = '%(function)s(%(distinct)s%(expressions)s)'

    def __init__(self, expression, separator=",", distinct=False, **extra):
        super(StringConcat, self).__init__(
            expression,
            Value(separator),
            distinct='DISTINCT ' if distinct else '',
            output_field=CharField(),
            **extra
        )

    def as_postgresql(self, compiler, connection):
        self.function = 'STRING_AGG'
        return super(StringConcat, self).as_sql(compiler, connection)


class DSum(Aggregate):
    function = 'SUM'
    template = '%(function)s(DISTINCT %(expressions)s)'
    name = 'Sum'
