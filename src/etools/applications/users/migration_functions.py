from django.db.models import F


def copy_user_emails_to_usernames(apps, schema):
    User = apps.get_model('auth.User')

    # For users where their username is not the same as their email,
    # copy their email to their username.
    # This is needed since Django 1.10 increased the length of the username
    # field, and users with long emails created before then would have had
    # their usernames contain a truncated version of their email.
    User.objects.exclude(username__iexact=F('email')).update(username=F('email'))
