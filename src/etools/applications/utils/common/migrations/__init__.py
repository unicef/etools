# This package needed django to consider this app as migrated. Otherwise django synchronize
# test models before migration of other apps, in particular contenttypes. In this case migration
# crash because we use ContentType models in test models.
