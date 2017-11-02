from django.conf.urls import url

from features.views import get_flags

urlpatterns = (
    url(r'^flags/$',
        view=get_flags,
        name='flags-list'),

)
