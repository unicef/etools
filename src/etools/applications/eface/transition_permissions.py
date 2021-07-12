def user_is_partner_focal_point_permission(form, user):
    return form.intervention.partner_focal_points.filter(email=user.email).exists()


def user_is_programme_officer_permission(form, user):
    return form.intervention.unicef_focal_points.filter(email=user.email).exists()
