import datetime
import typing

from dateutil.relativedelta import relativedelta


class Quarter(typing.NamedTuple):
    quarter: int
    start: datetime.date
    end: datetime.date


def get_quarters_range(start: datetime.date, end: datetime.date) -> typing.List[Quarter]:
    """first date included, last excluded for every period in range"""
    if not start or not end:
        return []

    quarters = []
    i = 0
    while start < end:
        quarter_end = start + relativedelta(months=3) - relativedelta(days=1)
        period_end = min(quarter_end, end)
        quarters.append(Quarter(i + 1, start, period_end))
        start = quarter_end + relativedelta(days=1)
        i += 1

    return quarters
