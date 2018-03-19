from django.conf.urls import url

from attachments.views import AttachmentListView

urlpatterns = (
    url(
        r'^$',
        view=AttachmentListView.as_view(),
        name='list'
    ),
)
