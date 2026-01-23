from django.db import migrations, models
from django.utils.translation import gettext_lazy as _


class Migration(migrations.Migration):

    dependencies = [
        ("partners", "0006_add_accountability_to_affected_populations"),
    ]

    operations = [
        migrations.AddField(
            model_name="intervention",
            name="partner_selection_modality",
            field=models.CharField(
                blank=True,
                choices=[("open", _("Open selection")), ("direct", _("Direct selection"))],
                default="",
                help_text=_("Select how the partner was selected in UNPP (Open selection or Direct selection)."),
                max_length=16,
                null=True,
                verbose_name=_("Partner Selection Modality"),
            ),
        ),
    ]

