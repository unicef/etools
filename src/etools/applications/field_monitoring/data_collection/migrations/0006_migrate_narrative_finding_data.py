# Generated manually on 2026-02-12
# Data migration to migrate existing narrative_finding to narrative_finding_raw
# and clean the narrative_finding column

import re
from html.parser import HTMLParser

from django.db import migrations


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
    """
    Clean HTML and MS Word formatting tags from narrative finding text.
    """
    if not text:
        return ''
    
    # Strip HTML tags
    stripper = HTMLTagStripper()
    try:
        stripper.feed(text)
        cleaned = stripper.get_data()
    except Exception:
        # If HTML parsing fails, fall back to regex
        cleaned = text
    
    # Remove common MS Word XML tags and styling
    cleaned = re.sub(r'</?w:[^>]+>', '', cleaned)
    
    # Remove remaining HTML/XML tags
    cleaned = re.sub(r'<[^>]+>', '', cleaned)
    
    # Remove MS Word specific characters and artifacts
    cleaned = re.sub(r'&nbsp;', ' ', cleaned)
    cleaned = re.sub(r'&[a-zA-Z]+;', '', cleaned)
    
    # Clean up excessive whitespace
    cleaned = re.sub(r'\s+', ' ', cleaned)
    cleaned = cleaned.strip()
    
    return cleaned


def migrate_findings(model_class):
    """Generic migration function for narrative findings"""
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


def migrate_checklist_overall_findings(apps, schema_editor):
    """Migrate ChecklistOverallFinding narrative_finding data"""
    ChecklistOverallFinding = apps.get_model('field_monitoring_data_collection', 'ChecklistOverallFinding')
    migrate_findings(ChecklistOverallFinding)


def migrate_activity_overall_findings(apps, schema_editor):
    """Migrate ActivityOverallFinding narrative_finding data"""
    ActivityOverallFinding = apps.get_model('field_monitoring_data_collection', 'ActivityOverallFinding')
    migrate_findings(ActivityOverallFinding)


def reverse_findings(model_class):
    """Generic reverse function for narrative findings"""
    findings = list(model_class.objects.all())
    for finding in findings:
        if finding.narrative_finding_raw:
            finding.narrative_finding = finding.narrative_finding_raw
    
    if findings:
        model_class.objects.bulk_update(findings, ['narrative_finding'], batch_size=500)


def reverse_migration(apps, schema_editor):
    """Reverse migration - restore narrative_finding from narrative_finding_raw"""
    ChecklistOverallFinding = apps.get_model('field_monitoring_data_collection', 'ChecklistOverallFinding')
    ActivityOverallFinding = apps.get_model('field_monitoring_data_collection', 'ActivityOverallFinding')
    
    reverse_findings(ChecklistOverallFinding)
    reverse_findings(ActivityOverallFinding)


class Migration(migrations.Migration):

    dependencies = [
        ('field_monitoring_data_collection', '0005_add_narrative_finding_raw'),
    ]

    operations = [
        migrations.RunPython(migrate_checklist_overall_findings, reverse_migration),
        migrations.RunPython(migrate_activity_overall_findings, reverse_migration),
    ]
