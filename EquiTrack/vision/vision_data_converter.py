import datetime
import re
from itertools import groupby
from operator import itemgetter


def convert_vision_value(key, value):
    if type(value) == unicode:
        try:
            encoded_value = value.encode('ascii', 'ignore')
            return int(encoded_value)
        except ValueError:
            pass

    if isinstance(value, basestring):
        matched_date = re.match(r'/Date\((\d+)\)/', value, re.I)
        if matched_date:
            return datetime.datetime.fromtimestamp(int(matched_date.group(1)) / 1000.0)

    if key == 'WBS_REFERENCE' and value:
        return re.sub(r'(.{4})(.{2})(.{2})', r'\1/\2/\3/', value[0:11])

    return value


def format_records(records, order_info):
    def _to_dict(record_order, record_items):
        result = dict(zip(order_info, record_order))
        result.update({'ITEMS': list(record_items)})
        return result

    return [_to_dict(order, items) for order, items in groupby(records, key=itemgetter(*order_info))]
