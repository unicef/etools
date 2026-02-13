"""
Populate a Monitoring Activity with lots of data to stress-test PDF export performance.

Usage:
    python manage.py populate_activity_pdf_data 31
    python manage.py populate_activity_pdf_data 31 --schema afghanistan
    python manage.py populate_activity_pdf_data 31 --checklists 25 --questions 30 --action-points 15 --attachments 25
"""
from django.core.management.base import BaseCommand
from django.db import connection
from django.db.models import Q
from django.utils import timezone
from django_tenants.utils import get_tenant_model

from etools.applications.action_points.categories.models import Category
from etools.applications.action_points.tests.factories import ActionPointCommentFactory
from etools.applications.attachments.tests.factories import AttachmentFactory, AttachmentLinkFactory
from etools.applications.field_monitoring.data_collection.models import (
    ActivityOverallFinding,
    ActivityQuestion,
    ActivityQuestionOverallFinding,
    ChecklistOverallFinding,
    StartedChecklist,
)
from etools.applications.field_monitoring.fm_settings.models import Method, Option, Question
from etools.applications.field_monitoring.planning.models import MonitoringActivity, MonitoringActivityActionPoint


class Command(BaseCommand):
    help = "Populate a Monitoring Activity with lots of data so PDF export takes >5 seconds"

    def add_arguments(self, parser):
        parser.add_argument('activity_id', type=int, help='Monitoring Activity ID (e.g. 31)')
        parser.add_argument(
            '--checklists', type=int, default=20,
            help='Number of checklists to create (default: 20)',
        )
        parser.add_argument(
            '--questions', type=int, default=25,
            help='Number of activity questions to create (default: 25)',
        )
        parser.add_argument(
            '--action-points', type=int, default=12,
            help='Number of action points to create (default: 12)',
        )
        parser.add_argument(
            '--attachments', type=int, default=20,
            help='Total attachments for report + related + checklist (default: 20)',
        )
        parser.add_argument(
            '--schema', type=str, default=None,
            help='Tenant schema name (e.g. afghanistan). Queries run in schema afghanistan.* (default: current)',
        )

    def handle(self, *args, **options):
        activity_id = options['activity_id']
        n_checklists = options['checklists']
        n_questions = options['questions']
        n_action_points = options['action_points']
        n_attachments = options['attachments']
        schema_name = options.get('schema')

        # Set tenant/schema (e.g. afghanistan) so queries use schema_name.table_name
        # Tenant model lives in public schema - must query from public
        if schema_name:
            connection.set_schema_to_public()
            try:
                tenant = get_tenant_model().objects.get(
                    Q(schema_name=schema_name) | Q(name=schema_name) | Q(country_short_code=schema_name)
                )
            except get_tenant_model().DoesNotExist:
                self.stderr.write(self.style.ERROR(
                    f'Tenant/schema "{schema_name}" not found. '
                    'Use schema_name, name, or country_short_code.'
                ))
                return
            connection.set_tenant(tenant)
            self.stdout.write(f'Using tenant: {tenant.schema_name} ({tenant.name})')

        try:
            ma = MonitoringActivity.objects.get(pk=activity_id)
        except MonitoringActivity.DoesNotExist:
            self.stderr.write(self.style.ERROR(f'Activity {activity_id} not found'))
            return

        self.stdout.write(f'Populating activity {activity_id} ({ma.reference_number})...')

        # Ensure activity has at least one partner/cp_output for overall findings
        if not ma.partners.exists() and not ma.cp_outputs.exists():
            self.stdout.write(self.style.WARNING(
                'Activity has no partners or cp_outputs. Adding first available partner for relations.'
            ))
            from etools.applications.partners.models import PartnerOrganization
            partner = PartnerOrganization.objects.first()
            if partner:
                ma.partners.add(partner)
            if not ma.cp_outputs.exists():
                from etools.applications.reports.models import Result
                cp = Result.objects.filter(result_type__name='Output').first()
                if cp:
                    ma.cp_outputs.add(cp)

        # Get or create method
        method, _ = Method.objects.get_or_create(
            short_name='PDF_STRESS',
            defaults={'name': 'PDF Stress Test Method'}
        )

        # Get category for Question
        from etools.applications.field_monitoring.fm_settings.models import Category as QuestionCategory
        cat = QuestionCategory.objects.first()
        if not cat:
            cat = QuestionCategory.objects.create(name='PDF Stress')

        # Create questions with likert_scale/multiple_choice (triggers N+1 in export)
        questions_with_options = []
        for i in range(n_questions):
            answer_type = 'likert_scale' if i % 2 == 0 else 'multiple_choice'
            q = Question.objects.create(
                category=cat,
                answer_type=answer_type,
                level='partner',
                text=f'Stress test question {i + 1}',
                is_custom=True,
                choices_size=3,
            )
            q.methods.add(method)
            for j in range(3):
                Option.objects.create(question=q, label=f'Option {j}', value=f'opt_{i}_{j}')
            questions_with_options.append(q)

        # Create activity questions linked to partners/cp_outputs
        target_partner = ma.partners.first()
        target_cp = ma.cp_outputs.first()
        activity_questions = []
        for i, q in enumerate(questions_with_options):
            aq = ActivityQuestion.objects.create(
                monitoring_activity=ma,
                question=q,
                text=q.text,
                is_enabled=True,
                partner=target_partner,
                cp_output=target_cp,
            )
            activity_questions.append(aq)
            # Activity question overall finding (for get_export_activity_questions_overall_findings)
            opt = q.options.first()
            ActivityQuestionOverallFinding.objects.create(
                activity_question=aq,
                value=opt.value if q.answer_type == 'likert_scale' else [opt.value],
            )

        # Activity overall findings (one per partner/cp_output)
        for p in ma.partners.all()[:3]:
            ActivityOverallFinding.objects.get_or_create(
                monitoring_activity=ma,
                partner=p,
                defaults={'narrative_finding': f'Narrative for partner {p}', 'on_track': True},
            )
        for c in ma.cp_outputs.all()[:3]:
            ActivityOverallFinding.objects.get_or_create(
                monitoring_activity=ma,
                cp_output=c,
                defaults={'narrative_finding': f'Narrative for output {c}', 'on_track': True},
            )

        # Create checklists with overall findings and findings
        user = ma.visit_lead or ma.team_members.first()
        if not user:
            from django.contrib.auth import get_user_model
            user = get_user_model().objects.filter(is_staff=True).first()
        if not user:
            self.stderr.write(self.style.ERROR('No user for checklist author. Ensure activity has visit_lead or team_members.'))
            return

        # StartedChecklist.save() auto-creates findings and overall findings from activity.questions
        for i in range(n_checklists):
            StartedChecklist.objects.create(
                monitoring_activity=ma,
                method=method,
                information_source=f'Source {i}',
                author=user,
            )

        # Create action points with comments
        ap_category = Category.objects.filter(module=Category.MODULE_CHOICES.fm).first()
        if not ap_category:
            ap_category = Category.objects.create(module=Category.MODULE_CHOICES.fm, description='FM Stress')
        section = ma.sections.first()
        office = user.profile.tenant_profile.office if hasattr(user, 'profile') and getattr(user.profile, 'tenant_profile', None) else None
        for i in range(n_action_points):
            ap = MonitoringActivityActionPoint.objects.create(
                monitoring_activity=ma,
                description=f'Action point {i + 1} for PDF stress test',
                due_date=timezone.now().date(),
                author=user,
                assigned_by=user,
                assigned_to=user,
                category=ap_category,
                section=section,
                office=office,
                status='open',
            )
            for j in range(2):
                ActionPointCommentFactory(
                    content_object=ap,
                    user=user,
                    comment=f'Comment {j} on action point {i}',
                )

        # Create attachments (report, related, checklist)
        report_count = n_attachments // 3
        related_count = n_attachments // 3
        checklist_count = n_attachments - report_count - related_count

        for i in range(report_count):
            att = AttachmentFactory(content_object=ma, code='report_attachments', uploaded_by=user)
            AttachmentLinkFactory(attachment=att, content_object=ma)

        for i in range(related_count):
            att = AttachmentFactory(content_object=ma, code='attachments', uploaded_by=user)
            AttachmentLinkFactory(attachment=att, content_object=ma)

        for cof in ChecklistOverallFinding.objects.filter(started_checklist__monitoring_activity=ma)[:checklist_count]:
            att = AttachmentFactory(content_object=cof, code='attachments', uploaded_by=user)
            AttachmentLinkFactory(attachment=att, content_object=cof)

        self.stdout.write(self.style.SUCCESS(
            f'Done. Added ~{n_questions} questions, {n_checklists} checklists, '
            f'{n_action_points} action points, {n_attachments} attachments.'
        ))
        self.stdout.write(f'Try: GET /api/v1/field-monitoring/planning/activities/{activity_id}/pdf/')
