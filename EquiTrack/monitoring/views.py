from django.http import HttpResponse
from .service_checks import CHECKS, ServiceStatus


def check_everything(request):
    def run_test(test):
        try:
            return test()
        except Exception as e:
            message = "EXCEPTION: {}".format(repr(e))
            return ServiceStatus(False, message)

    results = {}
    for check_id, check_function in CHECKS.items():
        results[check_id] = run_test(check_function)

    if any(not r.success for r in results.values()):
        response = 'Problems with the following services:\n{}'.format(
            '\n'.join(
               '{}: {}'.format(service_id, result.message)
               for service_id, result in results.items() if not result.success
            )
        )
        return HttpResponse(response, status=500, content_type='text/plain')
    else:
        return HttpResponse(
            'all is well (checked: {})'.format(', '.join(results.keys())),
            content_type='text/plain',
        )
