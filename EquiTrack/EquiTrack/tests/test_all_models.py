from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import inspect
import sys
from unittest import skipIf, TestCase

from django.apps import apps

# EXCLUDED_PACKAGES are the packages we want to exclude from testing for Python-3 compatible __str__() implementations.
# If a 3rd party app model fails in TestStrMethods, feel free to add the package to this list. We aren't interested in
# testing 3rd party packages. If an eTools model fails in TestStrMethods, it needs to be fixed.
EXCLUDED_PACKAGES = (
    'actstream',
    'allauth',
    'corsheaders',
    'django',
    'djcelery',
    'easy_thumbnails',
    'rest_framework',
    'generic_links',
    'post_office',
    'reversion',

    # These are the eTools packages that aren't yet using @python_2_unicode_compatible and therefore aren't yet
    # Python 3-compatible. As they're fixed one by one, they'll be removed from this list.
    'attachments',
    'audit',
    'notification',
    'partners',
    'publics',
    'reports',
    'reversion',
    'trips',
    't2f',
    'users',
    'vision',
    'workplan',
    )


@skipIf(sys.version_info.major == 3, "This test can be deleted under Python 3")
class TestStrMethods(TestCase):
    '''Ensure all models in this project that implement __str__() or __unicode__() use the Django decorator
    python_2_unicode_compatible. Models from non-eTools packages are excluded; we're not interested in
    testing them.

    This works on a whitelist concept; all models are tested unless their package is in EXCLUDED_PACKAGES. This
    ensures that if any new packages or models are added to eTools, they'll be caught by this test.
    '''
    FAILURE_MESSAGE = "Model {} should use Django's @python_2_unicode_compatible decorator"

    def test_for_python_3_incompatible_methods(self):
        models = apps.get_models()
        for model in models:
            # model.__module__ is the module name (a string), not an actual module instance. It's something like
            # 'funds.models' or 'django.contrib.auth.models'.
            package_hierarchy = model.__module__.split('.')
            if (package_hierarchy[0] in EXCLUDED_PACKAGES) or ('tests' in package_hierarchy):
                # Skip this model. It's in a 3rd party package or a model that's only used in test.
                pass
            else:
                # An eTools model can be in one of 5 categories --
                #   1. Has the @python_2_unicode_compatible decorator. These models are guaranteed to have both
                #      __str__() and __unicode__() methods.
                #   2. Does not have the decorator; implements __str__()
                #   3. Does not have the decorator; implements __unicode__()
                #   4. Does not have the decorator; implements __str__() and __unicode__()
                #   5. Does not have the decorator; implements neither __str__() nor __unicode__()
                #
                # Category 1 is what we want most models to fall into. Those models pass this test.
                #
                # Categories 2, 3, and 4 models are failures from this test's perspective. All eTools models that
                # implement __str__() or __unicode__() must use @python_2_unicode_compatible decorator.
                #
                # Category 5 models pass this test because they're already compatible with Python 3.
                #
                # I can tell which category a model is in by comparing the results of inspect.getmodule(model.__str__)
                # and inspect.getmodule(model.__unicode__). Models in categories 2 and 5 don't have a __unicode__()
                # method at all (i.e. hasattr(model, '__unicode__') == False).
                #
                #  Category |   inspect.getmodule(model.__str__)   | inspect.getmodule(model.__unicode__) |
                #  ---------+--------------------------------------+--------------------------------------|
                #     1     |        django's six.py               |        the model's module            |
                #     2     |       the model's module             |                NA                    |
                #     3     |        django's base.py              |        the model's module            |
                #     4     |       the model's module             |        the model's module            |
                #     5     |        django's base.py              |                NA                    |

                # inspect.getmodule() returns an actual module instance. The module name is something like
                # 'django.utils.six', 'django.db.models.base', or 'partners.models'. I don't assume too much about
                # the location of Django's base or six in case they move in some future Django version.
                str_module_path = inspect.getmodule(model.__str__).__name__.split('.')
                if str_module_path[0] == 'django' and str_module_path[-1] == 'six':
                    # Category 1 -- you get a gold star!
                    pass
                else:
                    # This model falls into category 2, 3, 4, or 5.
                    if hasattr(model, '__unicode__'):
                        # Category 3 or 4.
                        raise AssertionError(self.FAILURE_MESSAGE.format(model))
                    else:
                        # Category 2 or 5.
                        if str_module_path[0] == 'django' and str_module_path[-1] == 'base':
                            # This is category 5. Good enough!
                            pass
                        else:
                            # This is category 2.
                            raise AssertionError(self.FAILURE_MESSAGE.format(model))
