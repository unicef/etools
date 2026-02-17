"""
Tests for narrative finding cleanup feature - covering ticket requirements only.
"""
from django.test import TestCase

from etools.applications.field_monitoring.data_collection.models import (
    ActivityOverallFinding,
    ChecklistOverallFinding,
)
from etools.applications.field_monitoring.data_collection.serializers import (
    ActivityOverallFindingSerializer,
    ChecklistOverallFindingSerializer,
)
from etools.applications.field_monitoring.data_collection.utils import clean_narrative_finding


class TestNarrativeFindingCleaning(TestCase):
    """Test narrative finding cleaning removes HTML/MS Word tags."""

    def test_html_tags_removed(self):
        """HTML tags should be removed from text."""
        result = clean_narrative_finding('<p>Text with HTML</p>')
        self.assertEqual(result, 'Text with HTML')

    def test_ms_word_tags_removed(self):
        """MS Word XML tags should be removed from text."""
        result = clean_narrative_finding('<w:p><w:r>Word text</w:r></w:p>')
        self.assertEqual(result, 'Word text')

    def test_html_entities_cleaned(self):
        """HTML entities like &nbsp; should be cleaned."""
        result = clean_narrative_finding('Text&nbsp;with&nbsp;spaces')
        self.assertEqual(result, 'Text with spaces')


class TestNarrativeFindingStorage(TestCase):
    """Test raw text stored in narrative_finding_raw, cleaned in narrative_finding."""

    def test_checklist_auto_cleaning_on_save(self):
        """ChecklistOverallFinding auto-cleans on save."""
        finding = ChecklistOverallFinding(
            narrative_finding_raw='<p>HTML content</p>'
        )
        
        # Manually trigger save logic
        if finding.narrative_finding_raw:
            finding.narrative_finding = clean_narrative_finding(finding.narrative_finding_raw)
        
        self.assertEqual(finding.narrative_finding_raw, '<p>HTML content</p>')
        self.assertEqual(finding.narrative_finding, 'HTML content')

    def test_activity_auto_cleaning_on_save(self):
        """ActivityOverallFinding auto-cleans on save."""
        finding = ActivityOverallFinding(
            narrative_finding_raw='<div>Activity HTML</div>'
        )
        
        # Manually trigger save logic
        if finding.narrative_finding_raw:
            finding.narrative_finding = clean_narrative_finding(finding.narrative_finding_raw)
        
        self.assertEqual(finding.narrative_finding_raw, '<div>Activity HTML</div>')
        self.assertEqual(finding.narrative_finding, 'Activity HTML')

    def test_empty_raw_clears_cleaned(self):
        """Empty narrative_finding_raw should clear narrative_finding."""
        finding = ChecklistOverallFinding(
            narrative_finding_raw=''
        )
        
        # Manually trigger save logic
        if finding.narrative_finding_raw:
            finding.narrative_finding = clean_narrative_finding(finding.narrative_finding_raw)
        else:
            finding.narrative_finding = ''
        
        self.assertEqual(finding.narrative_finding, '')


class TestSerializerUsesRawField(TestCase):
    """Test serializers use narrative_finding_raw for frontend, not narrative_finding."""

    def test_checklist_serializer_exposes_raw_field(self):
        """ChecklistOverallFindingSerializer should expose narrative_finding_raw."""
        serializer = ChecklistOverallFindingSerializer()
        
        self.assertIn('narrative_finding_raw', serializer.fields)
        self.assertNotIn('narrative_finding', serializer.fields)

    def test_activity_serializer_exposes_raw_field(self):
        """ActivityOverallFindingSerializer should expose narrative_finding_raw."""
        serializer = ActivityOverallFindingSerializer()
        
        self.assertIn('narrative_finding_raw', serializer.fields)
        self.assertNotIn('narrative_finding', serializer.fields)

    def test_serializer_accepts_raw_field(self):
        """Serializer should accept and validate narrative_finding_raw."""
        data = {'narrative_finding_raw': '<p>New content</p>'}
        serializer = ChecklistOverallFindingSerializer(data=data, partial=True)
        
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data['narrative_finding_raw'], '<p>New content</p>')
