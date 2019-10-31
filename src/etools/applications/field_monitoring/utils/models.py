from django.db.models import IntegerField, Subquery


class SQCount(Subquery):
    """
    Get number of objects from subquery as count on join may return incorrect results
    """
    template = "(SELECT count(*) FROM (%(subquery)s) _count)"
    output_field = IntegerField()
