"""
Management command to clean narrative findings.

This script migrates existing narrative_finding data to narrative_finding_raw
and stores cleaned versions in narrative_finding.

Usage:
    python manage.py clean_narrative_findings
    python manage.py clean_narrative_findings --dry-run
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from etools.applications.field_monitoring.data_collection.models import (
    ActivityOverallFinding,
    ChecklistOverallFinding,
)
from etools.applications.field_monitoring.data_collection.utils import clean_narrative_finding


class Command(BaseCommand):
    help = 'Clean narrative findings by migrating raw data and removing formatting tags'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            dest='dry_run',
            help='Run without making changes to the database',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(self.style.WARNING('Running in DRY RUN mode - no changes will be saved'))
        
        self._clean_model_findings(ChecklistOverallFinding, 'ChecklistOverallFinding', dry_run)
        self._clean_model_findings(ActivityOverallFinding, 'ActivityOverallFinding', dry_run)
        
        if dry_run:
            self.stdout.write(self.style.SUCCESS('\nDry run completed - no changes were saved'))
        else:
            self.stdout.write(self.style.SUCCESS('\nAll narrative findings cleaned successfully!'))

    def _clean_model_findings(self, model_class, model_name, dry_run):
        """Clean narrative findings for a given model"""
        self.stdout.write(f'\nProcessing {model_name} records...')
        
        findings = model_class.objects.exclude(narrative_finding='')
        total = findings.count()
        
        self.stdout.write(f'Found {total} {model_name} records with narrative_finding')
        
        if total == 0:
            return
        
        updated = []
        for i, finding in enumerate(findings, 1):
            if i % 100 == 0:
                self.stdout.write(f'  Processing {i}/{total}...')
            
            # Store original in raw field if not already set
            if not finding.narrative_finding_raw:
                finding.narrative_finding_raw = finding.narrative_finding
            
            # Clean the narrative_finding
            cleaned = clean_narrative_finding(finding.narrative_finding_raw)
            
            if finding.narrative_finding != cleaned:
                if dry_run:
                    self.stdout.write(
                        self.style.NOTICE(
                            f'  [DRY RUN] Would clean {model_name} {finding.id}:\n'
                            f'    Original: {finding.narrative_finding[:100]}...\n'
                            f'    Cleaned:  {cleaned[:100]}...'
                        )
                    )
                else:
                    finding.narrative_finding = cleaned
                    updated.append(finding)
        
        if not dry_run and updated:
            with transaction.atomic():
                model_class.objects.bulk_update(
                    updated,
                    ['narrative_finding_raw', 'narrative_finding'],
                    batch_size=500
                )
            self.stdout.write(
                self.style.SUCCESS(f'✓ Updated {len(updated)} {model_name} records')
            )
