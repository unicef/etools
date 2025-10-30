# Migration to restore ItemTransferHistory model conditionally

from django.db import migrations, models, connection
import django.db.models.deletion
import django.utils.timezone
import model_utils.fields


def table_exists(table_name):
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = %s
            );
        """, [table_name])
        return cursor.fetchone()[0]


def create_itemtransferhistory_if_not_exists(apps, schema_editor):
    if not table_exists('last_mile_itemtransferhistory'):
        ItemTransferHistory = apps.get_model('last_mile', 'ItemTransferHistory')
        schema_editor.create_model(ItemTransferHistory)
        print("Created last_mile_itemtransferhistory table")
    else:
        print("last_mile_itemtransferhistory table already exists, skipping creation")


def reverse_create_itemtransferhistory(apps, schema_editor):
    """Reverse operation - we don't want to delete the table on reverse to preserve data"""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('last_mile', '0014_pointofinterest_secondary_type'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.CreateModel(
                    name='ItemTransferHistory',
                    fields=[
                        ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                        ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                        ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                        ('transfer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='last_mile.transfer')),
                        ('item', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='last_mile.item')),
                    ],
                    options={
                        'unique_together': {('transfer', 'item')},
                    },
                ),
                migrations.AddField(
                    model_name='item',
                    name='transfers_history',
                    field=models.ManyToManyField(through='last_mile.ItemTransferHistory', to='last_mile.transfer'),
                ),
            ],
            database_operations=[
                migrations.RunPython(
                    create_itemtransferhistory_if_not_exists,
                    reverse_create_itemtransferhistory,
                ),
            ],
        ),
    ]