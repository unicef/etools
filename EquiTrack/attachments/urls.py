from django.conf.urls import url

from attachments.views import AttachmentListView, FileUploadView

urlpatterns = (
    url(
        r'^upload/(?P<pk>\d+)/$',
        view=FileUploadView.as_view(),
        name='upload'
    ),
    url(
        r'^$',
        view=AttachmentListView.as_view(),
        name='list'
    ),
)
