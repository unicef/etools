from django.conf.urls import url

from attachments.views import FileUploadView

urlpatterns = (
    url(
        r'^upload/(?P<pk>\d+)/$',
        view=FileUploadView.as_view(),
        name='upload'
    ),
)
