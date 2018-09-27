import datetime
import json

from django.conf import settings

import requests


def get_data_from_insight(endpoint, data={}):
    url = '{}/{}'.format(
        settings.VISION_URL,
        endpoint
    ).format(**data)

    response = requests.get(
        url,
        headers={'Content-Type': 'application/json'},
        auth=(settings.VISION_USER, settings.VISION_PASSWORD),
        verify=False
    )
    if response.status_code != 200:
        return False, 'Loading data from Vision Failed, status {}'.format(response.status_code)
    try:
        result = json.loads(response.json())
    except ValueError:
        return False, 'Loading data from Vision Failed, no valid response returned for data: {}'.format(data)
    return True, result


def wcf_json_date_as_datetime(jd):
    if jd is None:
        return None
    sign = jd[-7]
    if sign not in '-+' or len(jd) == 13:
        millisecs = int(jd[6:-2])
    else:
        millisecs = int(jd[6:-7])
        hh = int(jd[-7:-4])
        mm = int(jd[-4:-2])
        if sign == '-':
            mm = -mm
        millisecs += (hh * 60 + mm) * 60000
    return datetime.datetime(1970, 1, 1) \
        + datetime.timedelta(microseconds=millisecs * 1000)


def wcf_json_date_as_date(jd):
    if jd is None:
        return None
    sign = jd[-7]
    if sign not in '-+' or len(jd) == 13:
        millisecs = int(jd[6:-2])
    else:
        millisecs = int(jd[6:-7])
        hh = int(jd[-7:-4])
        mm = int(jd[-4:-2])
        if sign == '-':
            mm = -mm
        millisecs += (hh * 60 + mm) * 60000
    my_date = datetime.datetime(1970, 1, 1) + datetime.timedelta(microseconds=millisecs * 1000)
    return my_date.date()


def comp_decimals(y, x):
    def isclose(a, b, rel_tol=1e-09, abs_tol=0.0):
        return abs(a - b) <= max(rel_tol * max(abs(a), abs(b)), abs_tol)

    return isclose(float(x), float(y))
