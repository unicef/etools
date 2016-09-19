from EquiTrack import notification


def notify_comment_tagged_users(sender, instance, action, **kwargs):
    """
    Triggers notification for newly tagged users on Comment.
    """
    # Caches the original set of tagged users on the instance to be able to
    # determine new ones after update.
    if action == "pre_clear":
        instance.__tagged_users_old = {x.id for x in instance.tagged_users.all()}
    # Compare newly added to the old set
    if action == "post_add":
        tagged_users_new = {x.id for x in instance.tagged_users.all()}
        users_to_notify = list(tagged_users_new & set(tagged_users_new ^ instance.__tagged_users_old))
        # Trigger notification
        notification.notify_comment_tagged_users(users_to_notify, instance)
