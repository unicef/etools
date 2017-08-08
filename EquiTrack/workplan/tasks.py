from django.core import mail
from django.contrib.auth.models import User

from EquiTrack.celery import app
from workplan.models import Comment


@app.task
def notify_comment_tagged_users(user_ids, comment_id):
    """
    Notify users about being tagged on comments.
    """
    comment = Comment.objects.get(id=comment_id)
    users = User.objects.filter(id__in=user_ids)
    subject = "You are tagged on a comment"
    text = "You are tagged on the following comment:\n\n{}".format(comment.text)
    from_email = "info@etools.org"

    messages = [(subject, text, from_email, [x.email]) for x in users]
    mail.send_mass_mail(messages, fail_silently=False)
