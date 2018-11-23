from django.core.management import BaseCommand

from etools.applications.field_monitoring.conditions import FieldMonitoringModuleCondition
from etools.applications.field_monitoring.groups import FMUser, UNICEFUser
from etools.applications.permissions2.conditions import GroupCondition
from etools.applications.permissions2.models import Permission


class Command(BaseCommand):
    field_monitoring_settings = [
        'field_monitoring_settings.fmmethodtype.*',
        'field_monitoring_settings.locationsite.*',
        'reports.result.fm_config',
        'field_monitoring_settings.cpoutputconfig.*',
    ]
    field_monitoring_readable_settings = field_monitoring_settings + [
        'reports.result.*',
    ]

    fm_user = 'fm_user'
    unicef_user = 'unicef_user'
    data_collector = 'data_collector'

    user_roles = {
        fm_user: [GroupCondition.predicate_template.format(group=FMUser.name)],
        unicef_user: [GroupCondition.predicate_template.format(group=UNICEFUser.name)],
        data_collector: []
    }

    def _update_permissions(self, role, perm, targets, perm_type, condition=None):
        if isinstance(role, (list, tuple)):
            for r in role:
                self._update_permissions(r, perm, targets, perm_type, condition)
            return

        if isinstance(targets, str):
            targets = [targets]

        condition = (condition or []) + [FieldMonitoringModuleCondition()] + self.user_roles[role]

        if self.verbosity >= 3:
            for target in targets:
                print(
                    '   {} {} permission for {} on {}\n'
                    '      if {}.'.format(
                        'Add' if perm_type == 'allow' else 'Revoke',
                        perm,
                        role,
                        target,
                        condition,
                    )
                )

        self.defined_permissions.extend([
            Permission(target=target, permission=perm, permission_type=perm_type, condition=condition)
            for target in targets
        ])

    def add_permission(self, role, perm, targets, condition=None):
        self._update_permissions(role, perm, targets, 'allow', condition)

    def revoke_permission(self, role, perm, targets, condition=None):
        self._update_permissions(role, perm, targets, 'disallow', condition)

    def handle(self, *args, **options):
        self.verbosity = options.get('verbosity', 1)

        self.defined_permissions = []

        if self.verbosity >= 2:
            print(
                'Generating new permissions...'
            )

        self.assign_permissions()

        old_permissions = Permission.objects.filter(condition__contains=[FieldMonitoringModuleCondition.predicate])
        old_permissions_count = old_permissions.count()

        if self.verbosity >= 2:
            self.stdout.write(
                'Deleting old permissions...'
            )
        old_permissions.delete()

        if self.verbosity >= 2:
            self.stdout.write(
                'Creating new permissions...'
            )
        Permission.objects.bulk_create(self.defined_permissions)

        if self.verbosity >= 1:
            self.stdout.write(
                'Field Monitoring permissions updated ({}) -> ({}).'.format(
                    old_permissions_count, len(self.defined_permissions)
                )
            )

    def assign_permissions(self):
        self.add_permission(self.unicef_user, 'view', self.field_monitoring_readable_settings)
        self.add_permission(self.fm_user, 'edit', self.field_monitoring_settings)
