# -*- coding: utf-8 -*-
import datetime
import os
import dill as pickle
import decorator
from adminactions.export import ForeignKeysCollector
from django.db import IntegrityError
from django.test import Client
from django.urls import resolve

from etools.applications.users.tests.factories import UserFactory

try:
    from concurrency.api import disable_concurrency
except ImportError:
    disable_concurrency = lambda z: True  # noqa

FILENAME_BASE_RESPONSE = FILENAME_BASE_FIXTURE = '_recorder'


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


class Dummy(object):
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


class BaseAPIRecorder:
    def __init__(self, basedir) -> None:
        super().__init__()
        self.basedir = os.path.dirname(basedir)

    def get_filename(self, func=None, url=None, name=''):
        if func:
            filename = os.path.join(self.basedir, '_recorder',
                                    func.__module__,
                                    *func.__qualname__.split('.')) + '.pickle'
        elif url:
            filename = os.path.join(self.basedir, '_recorder',
                                    url[1:-1].replace('/', '-')) + '.pickle'
        else:
            filename = os.path.join(self.basedir, '_recorder', name + '.pickle')

        if not os.path.exists(filename):
            mktree(os.path.dirname(filename))
        return filename

    def memoize(self, func, *args, **kwargs):
        filename = self.get_filename(func)
        if not os.path.exists(filename):
            values = func(*args, **kwargs)
            collector = ForeignKeysCollector(None)
            collector.collect(values)
            pickle.dump(collector.data, open(filename, 'wb'))

    def _pickle(self, filename, values):
        if not os.path.exists(filename):
            print(f"Creating pickle file: `{filename}`")
            collector = ForeignKeysCollector(None)
            collector.collect(values)
            pickle.dump(collector.data, open(filename, 'wb'))
        try:
            # print(f"Loading pickle file: `{filename}`")
            values = pickle.load(open(filename, 'rb'))
            _visited = []
            for e in reversed(values):
                if e.__class__ not in _visited:
                    e.__class__.objects.all().delete()
                    _visited.append(e.__class__)
                if hasattr(e.__class__, 'tracker'):
                    e.__class__.tracker = None

                if hasattr(e.__class__, '_concurrencymeta'):
                    with disable_concurrency(e.__class__):
                        e.save()
                else:
                    e.save(force_insert=True)
            str(values[0])  # force unmarshall
            return values[0]
        except IntegrityError as e:
            raise IntegrityError('Invalid fixture {}: {}'.format(filename, e))
        except AttributeError as e:
            raise AttributeError('Invalid fixture {}: {}'.format(filename, e))

    def _unpickle(self, filename):
        try:
            # print(f"Loading pickle file: `{filename}`")
            values = pickle.load(open(filename, 'rb'))
            _visited = []
            for e in reversed(values):
                if e.__class__ not in _visited:
                    e.__class__.objects.all().delete()
                    _visited.append(e.__class__)
                if hasattr(e.__class__, 'tracker'):
                    e.__class__.tracker = None

                if hasattr(e.__class__, '_concurrencymeta'):
                    with disable_concurrency(e.__class__):
                        e.save()
                else:
                    e.save(force_insert=True)
            str(values[0])  # force unmarshall
            return values[0]
        except IntegrityError as e:
            raise IntegrityError('Invalid fixture {}: {}'.format(filename, e))
        except AttributeError as e:
            raise AttributeError('Invalid fixture {}: {}'.format(filename, e)) from e

    def record(self, factory):
        def inner(func):
            filename = self.get_filename(func)

            def wrapper(func, *args, **kwargs):
                factory._meta.model.tracker = None
                if not os.path.exists(filename):
                    args = func(*args, **kwargs)
                    ret = factory(**args)
                    self._pickle(filename, [ret])
                else:
                    ret = self._unpickle(filename)
                return ret

            return property(decorator.decorator(wrapper, func))

        return inner


class AssertModifiedMixin(BaseAPIRecorder):
    def assert_modified(self, value):
        assert datetime.datetime.strptime(value, '%Y-%m-%dT%H:%M:%S.%fZ')


class StandardAPIRecorder(AssertModifiedMixin, BaseAPIRecorder):
    pass


class ApiChecker:

    def setUp(self):
        super().setUp()
        self.user = UserFactory(username='user', is_staff=True)
        self.client = Client()
        self.client.login(username='user', password='test')

    def _compare_dict(self, response, stored, path='', view='unknown'):
        for field_name, v in response.items():
            if isinstance(v, dict):
                self._compare_dict(v, stored[field_name], f"{path}[{field_name}]", view=view)
            else:
                if v != stored[field_name]:
                    if hasattr(self.recorder, f'assert_{field_name}'):
                        asserter = getattr(self.recorder, f'assert_{field_name}')
                        asserter(response[field_name])
                    else:
                        raise AssertionError(rf"""View `{view}` breaks the contract.
Field `{field_name}` does not match.
- expected: `{stored[field_name]}`
- received: `{response[field_name]}`""")
                        #
                        # # FIXME: remove me (print)
                        # print(111, "aaaaaaaaaaaa", path, field_name, v, stored[field_name])

    def _compare(self, response, stored, filename, ignore_fields=None, view='unknown'):

        ignore_fields = ignore_fields or []
        assert isinstance(response, type(stored)), "response and stored do not match"
        if isinstance(response, (list, tuple)):
            response = response[0]
            stored = stored[0]

        for field in stored.keys():
            assert field in response.keys(), (rf"""View `{view}` breaks the contract.
Field `{field}` is missing in the new response""")

        self._compare_dict(response, stored, view=view)
        if not sorted(response.keys()) == sorted(stored.keys()):
            raise AssertionError(f"""View `{view}` returned more field than expected.
Test succeed but action needed {filename} tape need rebuild.
New fields are:
`%s`""" % [f for f in response.keys() if f not in stored.keys()])
        return True

    def _dump(self, response, filename):
        payload = response.json()
        c = Dummy(status_code=response.status_code,
                  content=response.content,
                  json=payload)
        pickle.dump(c, open(filename, 'wb'), -1)

    def assertAPI(self, url, allow_empty=False):
        match = resolve(url)
        view = match.func.cls

        name = os.path.join(self.__module__, self.__class__.__name__,
                            url[1:-1].replace('/', '-')
                            )

        filename = self.recorder.get_filename(name=name)
        response = self.client.get(url)
        payload = response.json()
        if not allow_empty and not payload:
            raise ValueError(f"View {view} returned and empty json. Check your test")

        if os.path.exists(filename):
            stored = pickle.load(open(filename, 'rb')).json
            self._compare(payload, stored, filename, view=view)
        else:
            self._dump(response, filename)

# class ViewSetChecher(ApiChecker):
#     URLS = []
#
#     def get_urls(self):
#         if self.URLS:
#             return self.URLS
#         raise ValueError("set URLS attribute or override `get_urls()`")
#
#     def get_fixtures(self):
#         pass
#
#     def testUrls(self):
#         style = color_style()
#         errors = []
#
#         print(f"{self.__class__.__name__}: - Check API contract")
#         for i, url in enumerate(self.get_urls()):
#             try:
#                 self.get_fixtures()
#                 sys.stdout.write(url)
#                 self.assertAPI(url)
#                 sys.stdout.write(style.SUCCESS(" PASSED\n"))
#             except AssertionError as e:
#                 errors.append(str(e))
#                 sys.stdout.write(style.ERROR(" FAIL\n"))
#             except Exception as e:
#                 sys.stdout.write(style.ERROR(" ERROR\n"))
#                 errors.append(str(e))
#
#         if errors:
#             assert False, "\n".join(errors)
#
#     def setUp(self):
#         super().setUp()
#         self.user = UserFactory(username='user', is_staff=True)
#         self.client = Client()
#         self.client.login(username='user', password='test')
