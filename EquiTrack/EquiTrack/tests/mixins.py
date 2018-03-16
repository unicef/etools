from django.core.urlresolvers import NoReverseMatch, reverse


def _delimit_namespace(namespace):
    '''Add delimiter (':') to namespace if necessary'''
    if namespace and not namespace.endswith(':'):
        namespace += ':'

    return namespace


class URLAssertionMixin(object):
    '''Mixin for any class derived from unittest.TestCase. Provides some assertion helpers for testing URL patterns'''

    def assertReversal(self, names_and_paths, namespace, url_prefix):
        '''Assert that all URLs in names_and_paths reverse as expected.

        names_and_paths should be a list/tuple of 3-tuples of (URL pattern name, URL suffix, kwargs), e.g. --
            (('intervention-list', '', {}),
             ('intervention-list-dash', 'dash/', {}),
             ('intervention-detail', '1/', {'pk': 1}), )

        namespace should be the invariant namespace for reversal, e.g. 'partners_api'

        url_prefix should be the invariant part of the expected URL, e.g. '/api/v2/interventions/'

        Using the examples above, this --
            reverse('partners_api:intervention-detail', {'pk': 1})
        will be compared to this --
            '/api/v2/interventions/1/'
        '''
        namespace = _delimit_namespace(namespace)

        for name, url_suffix, kwargs in names_and_paths:
            actual_url = reverse(namespace + name, kwargs=kwargs)
            expected_url = url_prefix + url_suffix
            self.assertEqual(actual_url, expected_url)

    def assertIntParamRegexes(self, names_and_paths, namespace):
        '''Assert that all URLs in names_and_paths that take int keyword args reject non-int args. non-int kwargs in
        URL patterns are ignored.

        See assertReversal() for an explanation of parameters.

        Limitation: int kwargs must be passed to this function as ints, not strings. Ints passed as strings won't be
        tested. For example --
        Correct:   {'pk': 1}
        Incorrect: {'pk': '1'}
        '''
        namespace = _delimit_namespace(namespace)

        # First, filter out patterns that don't use kwargs.
        names_and_paths = [(name, url_part, kwargs) for name, url_part, kwargs in names_and_paths if kwargs]

        # First, ensure these are reversible when given accetpable params. This ensures that when when NoReverseMatch
        # is raised below, it's raised for the right reason (param rejection) rather than for something that's not
        # being tested (e.g. incorrect namespace).
        for name, url_part, kwargs in names_and_paths:
            reverse(namespace + name, kwargs=kwargs)

        for invalid_value in (None, 'a', 'abc', '0x99', '-99'):
            for name, url_part, kwargs in names_and_paths:
                # Replace kwargs with a dict in which each int value is the invalid int.
                kwargs = {key: invalid_value for key, value in kwargs.items() if isinstance(value, int)}
                # The try/except below allows us to give an informative AssertionError. In Python 3, this can be
                # replaced with `with self.assertRaises(NoReverseMatch, msg=fail_msg):`
                try:
                    reverse(namespace + name, kwargs=kwargs)
                except NoReverseMatch:
                    # This is what we hope will happen.
                    pass
                else:
                    fail_msg = 'NoReverseMatch not raised for namespace={}, kwargs={}'.format(namespace + name, kwargs)
                    raise AssertionError(fail_msg)


class WorkspaceRequiredAPITestMixIn(object):
    """
    For BaseTenantTestCases that have a required workspace param, just automatically
    set the current tenant.
    """
    def forced_auth_req(self, method, url, user=None, data=None, request_format='json', **kwargs):
        data = data or {}
        data['workspace'] = self.tenant.business_area_code
        return super(WorkspaceRequiredAPITestMixIn, self).forced_auth_req(
            method, url, user=user, data=data, request_format=request_format, **kwargs
        )
