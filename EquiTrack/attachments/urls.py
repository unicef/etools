from django.conf.urls import url

from attachments import views

app_name = 'attachments'
urlpatterns = (
    url(
        r'^$',
        view=views.AttachmentListView.as_view(),
        name='list'
    ),
    url(
        r'^file/(?P<pk>\d+)/$',
        view=views.AttachmentFileView.as_view(),
        name='file'
    ),
    url(
        r'^upload/$',
        view=views.AttachmentCreateView.as_view(),
        name='create'
    ),
    url(
        r'^upload/(?P<pk>\d+)/$',
        view=views.AttachmentUpdateView.as_view(),
        name='update'
    ),
)
