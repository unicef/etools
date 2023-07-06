from django.core.management.commands import makemessages


# add make-messages command that allows you to skip fuzzy matching
class Command(makemessages.Command):
    msgmerge_options = makemessages.Command.msgmerge_options + ["--no-fuzzy-matching", ]
