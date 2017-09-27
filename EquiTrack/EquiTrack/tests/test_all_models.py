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
    'funds',
    'locations',
    'notification',
    'partners',
    'publics',
    'reports',
    'reversion',
    'supplies',
    'trips',
    't2f',
    'users',
    'vision',
    'workplan',
)


@skipIf(sys.version_info.major == 3, "This test can be deleted under Python 3")
class TestStrMethods(TestCase):
    '''Ensure all models in this project have Python-3 compatible __str__() methods implemented by the Django
    decorator python_2_unicode_compatible. Models from non-eTools packages are excluded; we're not interested in
    testing them.

    This works on a whitelist concept; all models are tested unless their package is in EXCLUDED_PACKAGES. This
    ensures that if any new packages or models are added to eTools, they'll be caught by this test.
    '''
    def test_for_non_default_str_method(self):
        '''Ensure all models have a __str__() method, and that the __unicode__() method is implemented as expected'''
        models = apps.get_models()
        for model in models:
            # model.__module__ is the module name (a string), not an actual module instance. It's something like
            # 'funds.models' or 'django.contrib.auth.models'.
            package_hierarchy = model.__module__.split('.')
            if (package_hierarchy[0] in EXCLUDED_PACKAGES) or ('tests' in package_hierarchy):
                # Skip this model. It's in a 3rd party package or a model that's only used in test.
                pass
            else:
                # Get the module that holds the __unicode__ implementation. inspect.getmodule() returns an actual
                # module instance.
                unicode_implementation_module = inspect.getmodule(model.__unicode__)
                # It's counterintuitive, but due to the way @python_2_unicode_compatible works, the __unicode__()
                # method should be implemented by eTools model code. It should *not* be implemented by the Django
                # model base class.
                # Models that implement __unicode__() but don't use the @python_2_unicode_compatible decorator will
                # pass this test but fail the next test.
                self.assertEqual(model.__module__, unicode_implementation_module.__name__)

                str_implementation_module = inspect.getmodule(model.__str__)
                # Again, counterintuitively, if the @python_2_unicode_compatible decorator is applied then the
                # implementation of __str__() will be in Django, specifically in django/utils/six.pyc. I don't want
                # to get too fussy about the name, though in case it changes from one Django verion to another.
                self.assertTrue(str_implementation_module.__name__.startswith('django.'))
                filename = str_implementation_module.__file__
                self.assertTrue(filename.endswith('six.pyc') or filename.endswith('six.py'))
