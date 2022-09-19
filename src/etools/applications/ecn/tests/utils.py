import json

from django.conf import settings


def get_example_ecn():
    with open(settings.PACKAGE_ROOT + '/applications/ecn/tests/example_ecn.json', 'r') as example_f:
        return json.loads(example_f.read())
