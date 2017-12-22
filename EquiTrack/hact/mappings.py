from __future__ import absolute_import, division, print_function, unicode_literals

import sys

# Each year the hact values dictionary may change
# these mappings are used to convert the data for the particular
# year into a standard format, which can be used by the serializer
# to export the data

STANDARD_FORMAT = {
    "planned_cash_transfer": "",
    "micro_assessment_needed": "",
    "programmatic_visits_planned": "",
    "programmatic_visits_required": "",
    "programmatic_visits_completed": "",
    "spot_checks_required": "",
    "spot_checks_completed": "",
    "audits_required": "",
    "audits_completed": "",
    "follow_up_flags": "",
}

# mapping is in descending order, from latest to oldest
# if no mapping found then first mapping in the list
# will be used
MAPPING = [
    ([2017], "map_2017"),
]


def map_hact_values(year, data):
    """Map hact values based on the year
    Default to the first function in the list if no matching year found
    """
    map_func = MAPPING[0][1]
    for year_list, func in MAPPING:
        if int(year) in year_list:
            map_func = func
            break
    return getattr(sys.modules[__name__], map_func)(data)


def map_2017(data):
    expected = {}
    for key in STANDARD_FORMAT.keys():
        if key in data.keys():
            expected[key] = data.get(key)

    try:
        visits_planned = data["programmatic_visits"]["planned"]["total"]
    except KeyError:
        visits_planned = None
    expected["programmatic_visits_planned"] = visits_planned

    try:
        visits_required = data["programmatic_visits"]["required"]["total"]
    except KeyError:
        visits_required = None
    expected["programmatic_visits_required"] = visits_required

    try:
        visits_completed = data["programmatic_visits"]["completed"]["total"]
    except KeyError:
        visits_completed = None
    expected["programmatic_visits_completed"] = visits_completed

    try:
        checks_required = data["spot_checks"]["required"]["total"]
    except KeyError:
        checks_required = None
    expected["spot_checks_required"] = checks_required

    try:
        checks_completed = data["spot_checks"]["completed"]["total"]
    except KeyError:
        checks_completed = None
    expected["spot_checks_completed"] = checks_completed

    try:
        audits_required = data["audits"]["required"]
    except KeyError:
        audits_required = None
    expected["audits_required"] = audits_required

    try:
        audits_completed = data["audits"]["completed"]
    except KeyError:
        audits_completed = None
    expected["audits_completed"] = audits_completed

    return expected
