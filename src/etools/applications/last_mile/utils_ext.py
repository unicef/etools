import json
from typing import Iterator

from django.db.models import QuerySet

from etools.libraries.pythonlib.encoders import CustomJSONEncoder


def stream_queryset_as_json(queryset: QuerySet) -> Iterator[str]:
    yield '['

    iterator = queryset.iterator()
    try:
        first_item = next(iterator)
        yield json.dumps(first_item, cls=CustomJSONEncoder)
    except StopIteration:
        yield ']'
        return
    for item in iterator:
        yield f',{json.dumps(item, cls=CustomJSONEncoder)}'
    yield ']'
