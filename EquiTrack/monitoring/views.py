from django.http import HttpResponse


def check_everything(request):
    return HttpResponse('all is well')
