from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from django.conf.urls import url

from features.views import get_flags

urlpatterns = (
    url(r'^flags/$',
        view=get_flags,
        name='flags-list'),

)
