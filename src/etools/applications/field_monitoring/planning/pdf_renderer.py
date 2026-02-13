"""
ReportLab-based PDF generator for Field Monitoring visit PDF.
Uses reportlab.platypus for fast native PDF generation.
"""
import html
import io
import re
from collections import defaultdict

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Image,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


def _strip_html(text):
    """Remove HTML tags and decode entities for plain text."""
    if not text:
        return "-"
    if not isinstance(text, str):
        return str(text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text or "-"


def _safe(value, default="-"):
    return value if value is not None and value != "" else default


def _escape(s):
    """Escape for ReportLab Paragraph XML (prevents literal <b> etc. and parsing breaks)."""
    if s is None:
        return ""
    return html.escape(str(s))


def build_visit_pdf(context):
    """
    Build visit PDF from context dict. Returns PDF bytes.
    Context keys: workspace, ma, field_offices, location, sections, team_members,
    partners, cp_outputs, interventions, overall_findings, summary_findings,
    data_collected, action_points, related_attachments, reported_attachments,
    checklist_attachments, mission_completion_date
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=0.85 * inch,
        leftMargin=0.85 * inch,
        topMargin=1 * inch,
        bottomMargin=1 * inch,
    )
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="Section",
            fontSize=16,
            textColor=colors.HexColor("#0099ff"),
            spaceAfter=6,
        )
    )
    styles.add(
        ParagraphStyle(
            name="Label",
            fontSize=12,
            fontName="Helvetica-Bold",
            spaceAfter=2,
        )
    )
    styles.add(
        ParagraphStyle(
            name="Value",
            fontSize=12,
            spaceAfter=8,
        )
    )
    styles.add(
        ParagraphStyle(
            name="VisitTitle",
            fontSize=20,
            textColor=colors.HexColor("#0099ff"),
            spaceAfter=12,
        )
    )

    story = []

    # Header
    try:
        from django.contrib.staticfiles import finders

        logo_path = finders.find("images/UNICEF_logo_with_text_white.png")
        if logo_path:
            img = Image(logo_path, width=3.17 * inch, height=0.5 * inch)
            workspace = _safe(context.get("workspace"), "-")
            header_data = [[img, Paragraph(f"<b>Workspace:</b> {workspace}", styles["Value"])]]
            header_table = Table(header_data, colWidths=[4 * inch, 3 * inch])
            header_table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#0099ff")),
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ]
                )
            )
            story.append(header_table)
    except Exception:
        pass
    story.append(Spacer(1, 12))

    ma = context["ma"]

    # Main info
    story.append(Paragraph(_escape(ma.reference_number), styles["VisitTitle"]))

    def _cell(label, value):
        """Label in bold via font tag (more reliable than <b> in Table cells)."""
        return Paragraph(
            f'<font name="Helvetica-Bold">{_escape(label)}</font> {_escape(value)}',
            styles["Value"],
        )

    info_data = [
        [
            _cell("Start Date:", ma.start_date.strftime('%d-%b-%y') if ma.start_date else '-'),
            _cell("End Date:", ma.end_date.strftime('%d-%b-%y') if ma.end_date else '-'),
        ],
        [
            _cell("Status:", ma.get_status_display()),
            _cell("Field offices:", context.get('field_offices')),
        ],
    ]
    mission_date = context.get("mission_completion_date")
    if mission_date:
        info_data.append([_cell("Mission completion date:", mission_date.strftime('%d-%b-%y')), ""])

    t = Table(info_data, colWidths=[3.5 * inch, 3.5 * inch])
    t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    story.append(t)
    story.append(Spacer(1, 12))

    def _row(label, value):
        story.append(Paragraph(f"<b>{_escape(label)}</b> {_escape(_safe(value))}", styles["Value"]))

    _row("Sections:", context.get("sections"))
    _row("Location:", context.get("location"))
    _row("Team Members:", context.get("team_members"))
    _row("Visit Lead:", str(ma.visit_lead) if ma.visit_lead else "-")
    story.append(Spacer(1, 8))

    # Entities
    story.append(Paragraph("ENTITIES TO MONITOR:", styles["Section"]))
    _row("Partner:", context.get("partners"))
    _row("CP Outputs:", context.get("cp_outputs"))
    _row("PD/SSFAS:", context.get("interventions"))
    story.append(Spacer(1, 8))

    # Overall findings
    story.append(Paragraph("OVERALL FINDING:", styles["Section"]))
    overall = list(context.get("overall_findings") or [])
    for item in overall:
        entity = _escape(_safe(item.get("entity_name")))
        story.append(Paragraph(f"<b>ENTITY:</b> {entity}", styles["Value"]))
        on_track = item.get("on_track")
        status = "On Track" if on_track is True else "Off Track" if on_track is False else "Not Monitored"
        story.append(Paragraph(f"<b>STATUS:</b> {status}", styles["Value"]))
        story.append(Paragraph(_escape(_strip_html(item.get("narrative_finding"))), styles["Value"]))
    story.append(Spacer(1, 8))

    # Summary findings
    story.append(Paragraph("SUMMARY FINDINGS:", styles["Section"]))
    summary = list(context.get("summary_findings") or [])
    by_entity = defaultdict(list)
    for s in summary:
        by_entity[_safe(s.get("entity_name"))].append(s)
    for entity_name, items in by_entity.items():
        story.append(Paragraph(f"<b>ENTITY:</b> {_escape(entity_name)}", styles["Value"]))
        qa_data = [[Paragraph(_escape(_strip_html(i.get("question_text", ""))), styles["Value"]), Paragraph(_escape(_strip_html(str(i.get("value", "")))), styles["Value"])] for i in items]
        qt = Table(qa_data, colWidths=[3.5 * inch, 3.5 * inch])
        qt.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.5, colors.grey), ("VALIGN", (0, 0), (-1, -1), "TOP")]))
        story.append(qt)
        story.append(Spacer(1, 6))
    story.append(Spacer(1, 8))

    # Data collected
    story.append(Paragraph("DATA COLLECTED:", styles["Section"]))
    data_collected = list(context.get("data_collected") or [])
    for ch in data_collected:
            _row("Team Member:", ch.get("team_member"))
            _row("Method:", ch.get("method"))
            _row("Source:", ch.get("source"))
            for ov in ch.get("overall", []):
                _row("Entity:", ov.get("entity_name"))
                _row("Overall Finding:", _strip_html(ov.get("narrative_finding")))
                qa = [[Paragraph(_escape(_strip_html(f.get("question_text", ""))), styles["Value"]), Paragraph(_escape(_strip_html(str(f.get("value", "")))), styles["Value"])] for f in ov.get("findings", [])]
                if qa:
                    ft = Table(qa, colWidths=[3.5 * inch, 3.5 * inch])
                    ft.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.5, colors.grey)]))
                    story.append(ft)
                story.append(Spacer(1, 6))
    story.append(Spacer(1, 8))

    # Related documents
    story.append(Paragraph("RELATED DOCUMENTS:", styles["Section"]))
    for att in context.get("related_attachments") or []:
        story.append(Paragraph(f"<b>Date Uploaded:</b> {_escape(att.get('date_uploaded', '-'))} | <b>Document Type:</b> {_escape(att.get('doc_type', '-'))}", styles["Value"]))
        story.append(Paragraph(f"<b>File:</b> {_escape(att.get('filename', '-'))} [{_escape(att.get('url_path', '-'))}]", styles["Value"]))
        story.append(Spacer(1, 4))
    story.append(Spacer(1, 8))

    # Reported documents
    story.append(Paragraph("REPORTED DOCUMENTS:", styles["Section"]))
    for att in context.get("reported_attachments") or []:
        story.append(Paragraph(f"<b>Date Uploaded:</b> {_escape(att.get('date_uploaded', '-'))} | <b>Document Type:</b> {_escape(att.get('doc_type', '-'))}", styles["Value"]))
        story.append(Paragraph(f"<b>File:</b> {_escape(att.get('filename', '-'))} [{_escape(att.get('url_path', '-'))}]", styles["Value"]))
        story.append(Spacer(1, 4))
    story.append(Spacer(1, 8))

    # Checklist documents
    story.append(Paragraph("CHECKLIST DOCUMENTS:", styles["Section"]))
    for att in context.get("checklist_attachments") or []:
        story.append(Paragraph(f"<b>Method:</b> {_escape(att.get('method', '-'))} | <b>Data Collector:</b> {_escape(att.get('data_collector', '-'))}", styles["Value"]))
        story.append(Paragraph(f"<b>Method Type:</b> {_escape(att.get('method_type', '-'))}", styles["Value"]))
        story.append(Paragraph(f"<b>Related To:</b> {_escape(att.get('related_to', '-'))} | <b>Related Name:</b> {_escape(att.get('related_name', '-'))}", styles["Value"]))
        story.append(Paragraph(f"<b>Date Uploaded:</b> {_escape(att.get('date_uploaded', '-'))} | <b>Document Type:</b> {_escape(att.get('doc_type', '-'))}", styles["Value"]))
        story.append(Paragraph(f"<b>File:</b> {_escape(att.get('filename', '-'))} [{_escape(att.get('url_path', '-'))}]", styles["Value"]))
        story.append(Spacer(1, 4))
    story.append(Spacer(1, 8))

    # Action points
    story.append(Paragraph("ACTION POINTS:", styles["Section"]))
    for i, ap in enumerate(context.get("action_points") or [], 1):
        story.append(Paragraph(f"<b>#{i}</b>", styles["Label"]))
        story.append(Paragraph(f"<b>Reference Number:</b> {_escape(ap.get('reference_number', '-'))}", styles["Value"]))
        story.append(Paragraph(f"<b>Is High Priority:</b> {_escape(ap.get('is_high_priority', '-'))}", styles["Value"]))
        story.append(Paragraph(f"<b>Description:</b> {_escape(_strip_html(ap.get('description', '')))}", styles["Value"]))

        ap_data = [
            [Paragraph(f"<b>Status:</b> {_escape(ap.get('status', '-'))}", styles["Value"]), Paragraph(f"<b>Due Date:</b> {_escape(ap.get('due_date', '-'))}", styles["Value"])],
            [Paragraph(f"<b>Assigned To:</b> {_escape(ap.get('assigned_to', '-'))}", styles["Value"]), Paragraph(f"<b>Assigned By:</b> {_escape(ap.get('assigned_by', '-'))}", styles["Value"])],
            [Paragraph(f"<b>Section:</b> {_escape(ap.get('section', '-'))}", styles["Value"]), Paragraph(f"<b>Office:</b> {_escape(ap.get('office', '-'))}", styles["Value"])],
            [Paragraph(f"<b>Related To:</b> {_escape(ap.get('related_to', '-'))}", styles["Value"]), Paragraph(f"<b>Category:</b> {_escape(ap.get('category', '-'))}", styles["Value"])],
        ]
        apt = Table(ap_data, colWidths=[3.5 * inch, 3.5 * inch])
        apt.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
        story.append(apt)

        story.append(Paragraph("<b>Actions Taken:</b>", styles["Label"]))
        for c in ap.get("comments", []):
            story.append(Paragraph(f"<b>Comment:</b> {_escape(_strip_html(c.get('comment', '')))}", styles["Value"]))
            story.append(Paragraph(f"<b>User:</b> {_escape(c.get('user', '-'))} | <b>Submit Date:</b> {_escape(c.get('submit_date', '-'))}", styles["Value"]))
            story.append(Paragraph(f"<b>Supporting document:</b> {_escape(c.get('filename', '-'))} [{_escape(c.get('url_path', '-'))}]", styles["Value"]))
            story.append(Spacer(1, 4))
        story.append(Spacer(1, 8))

    doc.build(story)
    return buffer.getvalue()
