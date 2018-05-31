# -*- coding: utf-8 -*-
"""
    DRF API Checker

This module offers some utilities to check DjangoRestFramework API endpoints variation.

The purpose is to guarantee that any code changes never introduce 'contract violations'
changing the Serialization behaviour.


Contract violations can happen when:

- fields are removed from Serializer
- field representation changes ( ie. date format)
- Response status code changes
- Response headers changes


How it works:

    The First time the test is ran, the response and model instances are serialized and
    saved on the disk; any further execution is checked against this first response. Model instances are saved as well,  to guarantee the same response's content.
Test data are saved in the same directory where the module test  lives, under `_api_checker/<module_fqn>/<test_class>`

Fields that cannot be checked by value can be tested writing custom `assert_<field_name>` methods. (see AssertModifiedMixin)
In case of nested objects, method must follow the field "path". (ie. `assert_permission_modified` vs `assert_modified`)

This module can also intercept when a field is added,
in this case it is mandatory recreate stored test data; simply delete them from the disk
or set `API_CHECKER_RESET` environment variable and run the test again,

How To use it:

```
class TestAPIAgreements(ApiChecker, AssertTimeStampedMixin, BaseTenantTestCase):

    def get_fixtures(self):
        return {'agreement': AgreementFactory(signed_by_unicef_date=datetime.date.today())}

    def test_agreement_detail(self):
        url = reverse("partners_api:agreement-detail", args=[self.get_fixture('agreement').pk])
        self.assertAPI(url)

    def test_agreement_list(self):
        url = reverse("partners_api:agreement-list")
        self.assertAPI(url)
```

or using ViewSetChecker

ViewSetChecker is custom test _type_, intended to be used as metaclass.
It will create a test for each url returned  by `get_urls()` in the format
`test__<normalized_url_path>`,  if a method with the same name is found the
creation is skipped reading this as an intention to have a custom test for that url.

```

class TestAPIIntervention(BaseTenantTestCase, metaclass=ViewSetChecker):

    def get_fixtures(cls):
        return {'intervention': InterventionFactory(id=101),
                'amendment': InterventionAmendmentFactory(),
                'result': InterventionResultLinkFactory(),
                }

    @classmethod
    def get_urls(self):
        return [
            reverse("partners_api:intervention-list"),
            reverse("partners_api:intervention-detail", args=[101]),
   §     ]

```
running this code will produce...

```
...
test_url__api_v2_interventions (etools.applications.partners.tests.test_api.TestAPIIntervention) ... ok
test_url__api_v2_interventions_101 (etools.applications.partners.tests.test_api.TestAPIIntervention) ... ok
...

```
in case something goes wrong the output will be

Field values mismatch:

AssertionError: View `<class 'etools.applications.partners.views.agreements_v2.AgreementListAPIView'>` breaks the contract.
Field `partner_name` does not match.
- expected: `Partner 0`
- received: `Partner 11`

Field removed:

AssertionError: View `<class 'etools.applications.partners.views.agreements_v2.AgreementListAPIView'>` breaks the contract.
Field `id` is missing in the new response

Field added:

AssertionError: View `<class 'etools.applications.partners.views.agreements_v2.AgreementListAPIView'>` returned more field than expected.
Action needed api_v2_agreements.response.json need rebuild.
New fields are:
`['country_programme']`


"""
import datetime
import inspect
import json
import os

from django.core import serializers as ser
from django.db import DEFAULT_DB_ALIAS, router
from django.test import Client
from django.urls import resolve

from adminactions.export import ForeignKeysCollector
from rest_framework.response import Response

from etools.applications.users.tests.factories import UserFactory

BASE_DATADIR = '_api_checker'
OVEWRITE = os.environ.get('API_CHECKER_RESET', False)


class ResponseEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, set):
            return list(obj)
        return json.JSONEncoder.default(self, obj)


def mktree(newdir):
    """works the way a good mkdir should :)
        - already exists, silently complete
        - regular file in the way, raise an exception
        - parent directory(ies) does not exist, make them as well
    """
    if os.path.isdir(newdir):
        pass
    elif os.path.isfile(newdir):
        raise OSError("a file with the same name as the desired "
                      "dir, '%s', already exists." % newdir)
    else:
        os.makedirs(newdir)


def _write(dest, content):
    if isinstance(dest, str):
        open(dest, 'wb').write(content)
    elif hasattr(dest, 'write'):
        dest.write(content)
    else:
        raise ValueError(f"'dest' must be a filepath or file-like object.It is {type(dest)}")


def _read(source):
    if isinstance(source, str):
        return open(source, 'rb').read()
    elif hasattr(source, 'read'):
        return source.read()
    raise ValueError("'source' must be a filepath or file-like object")


def dump_fixtures(fixtures, destination):
    data = {}
    j = ser.get_serializer('json')()

    for k, instances in fixtures.items():
        collector = ForeignKeysCollector(None)
        if isinstance(instances, (list, tuple)):
            data[k] = {'master': [],
                       'deps': []}
            for r in instances:
                collector.collect([r])
                ret = j.serialize(collector.data, use_natural_foreign_keys=False)
                data[k]['master'].append(json.loads(ret)[0])
                data[k]['deps'].append(json.loads(ret)[1:])
        else:
            collector.collect([instances])
            ret = j.serialize(collector.data, use_natural_foreign_keys=False)
            data[k] = {'master': json.loads(ret)[0],
                       'deps': json.loads(ret)[1:]}

    _write(destination, json.dumps(data, indent=4, cls=ResponseEncoder).encode('utf8'))


def load_fixtures(file, ignorenonexistent=False, using=DEFAULT_DB_ALIAS):
    content = json.loads(_read(file))
    ret = {}
    for name, struct in content.items():
        master = struct['master']
        deps = struct['deps']

        objects = ser.deserialize(
            'json', json.dumps([master] + deps), using=using, ignorenonexistent=ignorenonexistent,
        )
        saved = []
        for obj in objects:
            if router.allow_migrate_model(using, obj.object.__class__):
                obj.save(using=using)
                saved.append(obj.object)
        if isinstance(master, (list, tuple)):
            ret[name] = saved[:len(master)]
        else:
            ret[name] = saved[0]
    return ret


def serialize_response(response: Response):
    try:
        data = {'status_code': response.status_code,
                'headers': response._headers,
                'content': response.content.decode('utf8'),
                'data': response.data,
                'content_type': response.content_type,
                }
        return json.dumps(data, indent=4, cls=ResponseEncoder).encode('utf8')
    except Exception as e:
        raise e


def dump_response(response: Response, file):
    _write(file, serialize_response(response))


def load_response(file_or_stream):
    c = json.loads(_read(file_or_stream))
    r = Response(c['data'],
                 status=c['status_code'],
                 content_type=c['content_type'])
    r._headers = c['headers']
    return r


def clean_url(url):
    return url[1:-1].replace('/', '_')


class ApiChecker:
    """

    """

    def setUp(self):
        super().setUp()
        self.user = UserFactory(username='user', is_staff=True)
        self.client = Client()
        self.client.login(username='user', password='test')
        self._process_fixtures()

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.data_dir = os.path.join(os.path.dirname(inspect.getfile(cls)),
                                    BASE_DATADIR,
                                    cls.__module__, cls.__name__,
                                    )

    def _get_filename(self, name):
        filename = os.path.join(self.data_dir, name)
        if not os.path.exists(filename):
            mktree(os.path.dirname(filename))
        return filename

    def get_response_filename(self, url):
        return self._get_filename(clean_url(url) + '.response.json')

    def get_fixtures_filename(self, basename='fixtures'):
        return self._get_filename(f'{basename}.json')

    def get_fixtures(self):
        """ returns test fixtures.
        Should returns a dictionary where any key will be transformed in a
        test property and the value should be a Model instance.

        {'user' : UserFactory(username='user'),
         'partner': PartnerFactory(),
        }

        fixtures can be accessed using `get_fixture(<name>)`
        """
        return {}

    def get_fixture(self, name):
        """
        returns fixture `name` loaded by `get_fixtures()`
        """
        return self.__fixtures[name]

    def _process_fixtures(self):
        """ store or retrieve test fixtures """
        fname = self.get_fixtures_filename()
        if os.path.exists(fname):
            self.__fixtures = load_fixtures(fname)
        else:
            self.__fixtures = self.get_fixtures()
            if self.__fixtures:
                dump_fixtures(self.__fixtures, fname)

    def _compare_dict(self, response, stored, path='', view='unknown'):
        for field_name, v in response.items():
            if isinstance(v, dict):
                self._compare_dict(v, stored[field_name], f"{path}_{field_name}", view=view)
            else:
                if hasattr(self, f'assert_{path or field_name}'):
                    asserter = getattr(self, f'assert_{path or field_name}')
                    asserter(response, stored, path)
                else:
                    if isinstance(v, set):
                        v = list(v)

                    if field_name in stored and v != stored[field_name]:
                        raise AssertionError(rf"""View `{view}` breaks the contract.
Field `{field_name}` does not match.
- expected: `{stored[field_name]}`
- received: `{response[field_name]}`""")

    def _compare(self, response, stored, filename, ignore_fields=None, view='unknown'):

        # ignore_fields = ignore_fields or []
        # assert isinstance(response, type(stored)), "response and stored do not match"
        if isinstance(response, (list, tuple)):
            response = response[0]
            stored = stored[0]

        for field in stored.keys():
            assert field in response.keys(), (rf"""View `{view}` breaks the contract.
Field `{field}` is missing in the new response""")

        self._compare_dict(response, stored, view=view)
        if not sorted(response.keys()) == sorted(stored.keys()):
            raise AssertionError(f"""View `{view}` returned more field than expected.
Action needed {os.path.basename(filename)} need rebuild.
New fields are:
`%s`""" % [f for f in response.keys() if f not in stored.keys()])
        return True

    def assertAPI(self, url, allow_empty=False, headers=True, status=True):
        match = resolve(url)
        view = match.func.cls

        filename = self.get_response_filename(url)
        response = self.client.get(url)
        assert response.accepted_renderer
        payload = response.data
        if not allow_empty and not payload:
            raise ValueError(f"View {view} returned and empty json. Check your test")

        if not os.path.exists(filename) or OVEWRITE:
            dump_response(response, filename)

        stored = load_response(filename)
        if status:
            assert response.status_code == stored.status_code
        if headers:
            self._assert_headers(response, stored)
        self._compare(payload, stored.data, filename, view=view)

    def _assert_headers(self, response, stored):
        assert response['Content-Type'] == stored['Content-Type']
        assert sorted(response['Allow']) == sorted(stored['Allow'])


class ViewSetChecker(type):
    def __new__(cls, clsname, superclasses, attributedict):
        superclasses = (ApiChecker,) + superclasses
        clazz = type.__new__(cls, clsname, superclasses, attributedict)

        def check_url(url):
            def _inner(self):
                self.assertAPI(url)

            _inner.__name__ = "test_url__" + clean_url(u)
            return _inner

        for u in clazz.get_urls():
            m = check_url(u)
            if not hasattr(clazz, m.__name__):
                setattr(clazz, m.__name__, m)

        return clazz


class AssertTimeStampedMixin:
    def assert_modified(self, response: Response, stored: Response, path: str):
        value = response['modified']
        assert datetime.datetime.strptime(value, '%Y-%m-%dT%H:%M:%S.%fZ')

    def assert_created(self, response: Response, stored: Response, path: str):
        value = response['created']
        assert datetime.datetime.strptime(value, '%Y-%m-%dT%H:%M:%S.%fZ')
