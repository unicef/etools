# Generated manually on 2026-02-25
# Add narrative_finding_raw field and migrate existing data

import re
from html.parser import HTMLParser

from django.db import migrations, models


class HTMLTagStripper(HTMLParser):
    """HTML parser that strips all tags and returns clean text."""
    def __init__(self):
        super().__init__()
        self.reset()
        self.strict = False
        self.convert_charrefs = True
        self.text = []

    def handle_data(self, data):
        self.text.append(data)

    def get_data(self):
        return ''.join(self.text)


def clean_narrative_finding(text):
    """Clean HTML and MS Word formatting tags from narrative finding text."""
    if not text:
        return ''
    
    # Strip HTML tags
    stripper = HTMLTagStripper()
    try:
        stripper.feed(text)
        cleaned = stripper.get_data()
    except (ValueError, TypeError):
        cleaned = text
    
    # Remove MS Word XML tags
    cleaned = re.sub(r'</?w:[^>]+>', '', cleaned)
    # Remove remaining HTML/XML tags
    cleaned = re.sub(r'<[^>]+>', '', cleaned)
    # Remove HTML entities
    cleaned = re.sub(r'&nbsp;', ' ', cleaned)
    cleaned = re.sub(r'&[a-zA-Z]+;', '', cleaned)
    # Clean up whitespace
    cleaned = re.sub(r'\s+', ' ', cleaned)
    cleaned = cleaned.strip()
    
    return cleaned


def migrate_findings(model_class):
    """Migrate narrative findings to raw field and clean."""
    findings = list(model_class.objects.all())
    for finding in findings:
        if finding.narrative_finding:
            finding.narrative_finding_raw = finding.narrative_finding
            finding.narrative_finding = clean_narrative_finding(finding.narrative_finding)
    
    if findings:
        model_class.objects.bulk_update(
            findings, 
            ['narrative_finding_raw', 'narrative_finding'],
            batch_size=500
        )


def migrate_data_forward(apps, schema_editor):
    """Migrate existing narrative_finding data."""
    ChecklistOverallFinding = apps.get_model('field_monitoring_data_collection', 'ChecklistOverallFinding')
    ActivityOverallFinding = apps.get_model('field_monitoring_data_collection', 'ActivityOverallFinding')
    
    migrate_findings(ChecklistOverallFinding)
    migrate_findings(ActivityOverallFinding)


def reverse_data(apps, schema_editor):
    """Restore narrative_finding from narrative_finding_raw."""
    ChecklistOverallFinding = apps.get_model('field_monitoring_data_collection', 'ChecklistOverallFinding')
    ActivityOverallFinding = apps.get_model('field_monitoring_data_collection', 'ActivityOverallFinding')
    
    for model_class in [ChecklistOverallFinding, ActivityOverallFinding]:
        findings = list(model_class.objects.all())
        for finding in findings:
            if finding.narrative_finding_raw:
                finding.narrative_finding = finding.narrative_finding_raw
        
        if findings:
            model_class.objects.bulk_update(findings, ['narrative_finding'], batch_size=500)


class Migration(migrations.Migration):

    dependencies = [
        ('field_monitoring_data_collection', '0003_activityoverallfinding_ewp_activity_and_more'),
    ]

    operations = [
        # Add narrative_finding_raw field
        migrations.AddField(
            model_name='activityoverallfinding',
            name='narrative_finding_raw',
            field=models.TextField(blank=True, verbose_name='Narrative Finding Raw'),
        ),
        migrations.AddField(
            model_name='checklistoverallfinding',
            name='narrative_finding_raw',
            field=models.TextField(blank=True, verbose_name='Narrative Finding Raw'),
        ),
        # Migrate existing data
        migrations.RunPython(migrate_data_forward, reverse_data),
    ]
