from io import StringIO
from typing import Iterator

from django.db.models import QuerySet

from etools.libraries.pythonlib.encoders import CustomJSONEncoder


def stream_queryset_as_json(
    queryset: QuerySet,
    chunk_size: int = 1000,
    buffer_size: int = 50
) -> Iterator[str]:

    yield '['
    encoder = CustomJSONEncoder(ensure_ascii=False)
    iterator = queryset.iterator(chunk_size=chunk_size)
    buffer = StringIO()
    buffer_count = 0
    first = True

    for item in iterator:
        if first:
            buffer.write(encoder.encode(item))
            first = False
        else:
            buffer.write(',')
            buffer.write(encoder.encode(item))
        buffer_count += 1
        if buffer_count >= buffer_size:
            yield buffer.getvalue()
            buffer = StringIO()
            buffer_count = 0
    if buffer_count > 0:
        yield buffer.getvalue()

    yield ']'
