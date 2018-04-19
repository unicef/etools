from django.conf.urls import url

from attachments.views import AttachmentFileView, AttachmentListView

app_name = 'attachments'
urlpatterns = (
    url(
        r'^$',
        view=AttachmentListView.as_view(),
        name='list'
    ),
    url(
        r'^file/(?P<pk>\d+)/$',
        view=AttachmentFileView.as_view(),
        name='file'
    ),
)
