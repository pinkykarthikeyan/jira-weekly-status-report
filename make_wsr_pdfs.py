import csv
import os
from collections import Counter
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


CSV_PATH = r"C:\Users\PinkyAhmed\Downloads\sprint_101_status_updated.csv"
OUTPUT_DIR = r"C:\work\jira-weekly-status-report\output\pdf"
FULL_PDF = os.path.join(OUTPUT_DIR, "sprint_101_jira_engineering_wsr.pdf")
PROD_PDF = os.path.join(OUTPUT_DIR, "sprint_101_production_bugs.pdf")

NAVY = colors.HexColor("#1F4E78")
BLUE = colors.HexColor("#D9EAF7")
PALE_BLUE = colors.HexColor("#F3F6FA")
AMBER = colors.HexColor("#FFF2CC")
AMBER_TEXT = colors.HexColor("#7F6000")
RED = colors.HexColor("#F4CCCC")
RED_TEXT = colors.HexColor("#9C0006")
GRID = colors.HexColor("#D9E2F3")
TEXT = colors.HexColor("#1F2937")
MUTED = colors.HexColor("#5B6573")


def ascii_clean(value):
    replacements = {
        "\u2013": "-",
        "\u2014": "-",
        "\u2011": "-",
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u00a0": " ",
        "\u2003": " ",
        "\u200b": "",
        "\ufeff": "",
    }
    text = str(value or "")
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text.encode("ascii", "ignore").decode("ascii")


def parse_csv(path):
    issue_types = {"Bug", "Task", "Story", "Improvement"}
    with open(path, "r", encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.reader(stream))[1:]
    records = []
    for raw in rows:
        if not raw or not raw[0].strip():
            continue
        type_index = next(i for i, value in enumerate(raw[1:], 1) if value.strip() in issue_types)
        records.append(
            {
                "Key": raw[0].strip(),
                "Summary": ",".join(raw[1:type_index]).strip(),
                "Issue Type": raw[type_index].strip(),
                "Assignee": (raw[type_index + 1] if len(raw) > type_index + 1 else "").strip(),
                "Status": (raw[type_index + 2] if len(raw) > type_index + 2 else "").strip(),
                "Labels": ",".join(raw[type_index + 3:-1]).strip(),
                "Production Bug": raw[-1].strip(),
            }
        )
    return records


STATUS_ORDER = {
    "New / Open": 0,
    "In Progress": 1,
    "Ready for Testing": 2,
    "HerdX Accepted": 3,
    "Cannot Reproduce": 4,
    "Rejected / Not a Bug": 5,
    "Discarded": 6,
    "Done": 7,
}


def next_step(issue):
    if issue["Production Bug"] == "Yes":
        if issue["Status"] == "Ready for Testing":
            return "Complete production validation"
        if issue["Status"] == "New / Open":
            return "Triage and prioritize production fix"
        if issue["Status"] == "In Progress":
            return "Continue production fix"
        if issue["Status"] == "HerdX Accepted":
            return "Confirm disposition and close"
        if issue["Status"] == "Cannot Reproduce":
            return "Confirm reproduction outcome"
    if not issue["Assignee"]:
        return "Assign owner"
    if issue["Status"] == "New / Open":
        return "Triage and plan"
    if issue["Status"] == "In Progress":
        return "Continue development"
    if issue["Status"] == "Ready for Testing":
        return "Complete QA validation"
    if issue["Status"] == "HerdX Accepted":
        return "Confirm acceptance and close"
    if issue["Status"] == "Cannot Reproduce":
        return "Confirm reproduction outcome"
    if issue["Status"] == "Rejected / Not a Bug":
        return "Confirm closure"
    return "Review next action"


styles = getSampleStyleSheet()
TITLE = ParagraphStyle("Title", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=18, leading=22, textColor=TEXT, spaceAfter=3)
SUBTITLE = ParagraphStyle("Subtitle", parent=styles["Normal"], fontName="Helvetica-Oblique", fontSize=9.5, leading=12, textColor=MUTED, spaceAfter=10)
SECTION = ParagraphStyle("Section", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=10.5, leading=13, textColor=TEXT, spaceBefore=7, spaceAfter=4)
BODY = ParagraphStyle("Body", parent=styles["BodyText"], fontName="Helvetica", fontSize=8.6, leading=11, textColor=TEXT)
SMALL = ParagraphStyle("Small", parent=BODY, fontSize=7.8, leading=9.5)
TINY = ParagraphStyle("Tiny", parent=BODY, fontSize=6.8, leading=8.2)
HEADER = ParagraphStyle("Header", parent=BODY, fontName="Helvetica-Bold", fontSize=7.7, leading=9, textColor=colors.white, alignment=TA_CENTER)
LABEL = ParagraphStyle("Label", parent=BODY, fontName="Helvetica-Bold", textColor=MUTED)
FOOTER = ParagraphStyle("Footer", parent=BODY, fontSize=7.2, leading=8.5, textColor=MUTED)


def p(text, style=BODY):
    return Paragraph(escape(ascii_clean(text)).replace("\n", "<br/>").replace("  ", " &nbsp;"), style)


def section_bar(text, width):
    table = Table([[p(text, SECTION)]], colWidths=[width])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), BLUE),
        ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#9FBAD0")),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    return table


def table(data, widths, header=True, font_size=8.0, row_bands=True, status_col=None):
    converted = []
    for row_index, row in enumerate(data):
        converted.append([p(value, HEADER if header and row_index == 0 else (SMALL if font_size >= 7.5 else TINY)) for value in row])
    t = Table(converted, colWidths=widths, repeatRows=1 if header else 0, hAlign="LEFT")
    commands = [
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("BOX", (0, 0), (-1, -1), 0.6, GRID),
        ("INNERGRID", (0, 0), (-1, -1), 0.35, GRID),
    ]
    if header:
        commands.append(("BACKGROUND", (0, 0), (-1, 0), NAVY))
    for row_index in range(1 if header else 0, len(data)):
        if row_bands and (row_index - (1 if header else 0)) % 2 == 1:
            commands.append(("BACKGROUND", (0, row_index), (-1, row_index), PALE_BLUE))
    if status_col is not None:
        for row_index, row in enumerate(data[1:], 1):
            status = row[status_col]
            if status in {"New / Open", "Cannot Reproduce"}:
                commands.append(("BACKGROUND", (status_col, row_index), (status_col, row_index), AMBER))
                commands.append(("TEXTCOLOR", (status_col, row_index), (status_col, row_index), AMBER_TEXT))
            elif status == "In Progress":
                commands.append(("BACKGROUND", (status_col, row_index), (status_col, row_index), colors.HexColor("#FFF2CC")))
                commands.append(("TEXTCOLOR", (status_col, row_index), (status_col, row_index), AMBER_TEXT))
            elif status == "Ready for Testing":
                commands.append(("BACKGROUND", (status_col, row_index), (status_col, row_index), colors.HexColor("#DDEBF7")))
                commands.append(("TEXTCOLOR", (status_col, row_index), (status_col, row_index), NAVY))
            elif status == "Done":
                commands.append(("BACKGROUND", (status_col, row_index), (status_col, row_index), colors.HexColor("#E2F0D9")))
    t.setStyle(TableStyle(commands))
    return t


def footer(canvas, doc):
    canvas.saveState()
    width, _ = landscape(A4)
    canvas.setStrokeColor(GRID)
    canvas.setLineWidth(0.5)
    canvas.line(doc.leftMargin, 12 * mm, width - doc.rightMargin, 12 * mm)
    canvas.setFont("Helvetica", 7.2)
    canvas.setFillColor(MUTED)
    canvas.drawString(doc.leftMargin, 7 * mm, "Sprint 101 | Source: sprint_101_status_updated.csv")
    canvas.drawRightString(width - doc.rightMargin, 7 * mm, f"Page {doc.page}")
    canvas.restoreState()


def build_full_pdf(records):
    width, height = landscape(A4)
    margin = 14 * mm
    doc = SimpleDocTemplate(FULL_PDF, pagesize=landscape(A4), leftMargin=margin, rightMargin=margin, topMargin=12 * mm, bottomMargin=18 * mm)
    total = len(records)
    done = sum(r["Status"] == "Done" for r in records)
    active = [r for r in records if r["Status"] != "Done"]
    prod = [r for r in records if r["Production Bug"] == "Yes"]
    active_prod = [r for r in prod if r["Status"] != "Done"]
    status_counts = Counter(r["Status"] for r in records)
    prod_status_counts = Counter(r["Status"] for r in prod)
    type_counts = Counter(r["Issue Type"] for r in records)
    deployment = [r for r in records if "deployment" in r["Labels"].lower()]
    qa_auto_open = [r for r in records if "qaautomation" in r["Labels"].lower() and r["Status"] != "Done"]
    unassigned_active = [r for r in active if not r["Assignee"]]

    story = [
        p("WEEKLY ENGINEERING STATUS REPORT", TITLE),
        p("Sprint 101 status extract | As of 2026-09-08 | Source: sprint_101_status_updated.csv", SUBTITLE),
        table([
            ["Report period", "Sprint 101", "Team", "HA30 Engineering", "Overall status", "Amber"],
            ["Scope", f"{total} Jira records", "Done", str(done), "Active issues", str(len(active))],
            ["Production bugs", str(len(prod)), "Active production bugs", str(len(active_prod)), "Completion rate", f"{done / total:.1%}"],
        ], [90, 90, 70, 120, 90, 90], header=False, font_size=8.2, row_bands=False),
        Spacer(1, 7),
        section_bar("1. Completed This Week", width - 2 * margin),
        Spacer(1, 3),
        table([
            ["Metric", "Value", "Issue type", "Count"],
            ["Total issues in extract", str(total), "Bug", str(type_counts["Bug"])],
            ["Done", str(done), "Task", str(type_counts["Task"])],
            ["Completion rate", f"{done / total:.1%}", "Story", str(type_counts["Story"])],
            ["Production bugs total", str(len(prod)), "Improvement", str(type_counts["Improvement"])],
            ["Production bugs still active", str(len(active_prod)), "Deployment-tagged", str(len(deployment))],
            ["Active issues", str(len(active)), "QA automation", str(sum("qaautomation" in r["Labels"].lower() for r in records))],
        ], [145, 70, 145, 70], font_size=8.2),
        Spacer(1, 7),
        section_bar("2. In Progress", width - 2 * margin),
        Spacer(1, 3),
    ]
    statuses = ["New / Open", "In Progress", "Ready for Testing", "HerdX Accepted", "Rejected / Not a Bug", "Cannot Reproduce", "Discarded"]
    in_progress_rows = [["Status", "Issue count", "Production bugs", "Share of extract"]]
    for status in statuses:
        count = status_counts[status]
        prod_count = prod_status_counts[status]
        in_progress_rows.append([status, str(count), str(prod_count), f"{count / total:.1%}"])
    in_progress_rows.append(["Total not Done", str(len(active)), str(len(active_prod)), f"{len(active) / total:.1%}"])
    story.append(table(in_progress_rows, [180, 100, 120, 120], font_size=8.2, status_col=0))
    story += [PageBreak(), section_bar("3. Blocked or At Risk", width - 2 * margin), Spacer(1, 3)]
    story.append(table([
        ["Risk / issue", "Count", "Action / reference"],
        ["Active production bugs", str(len(active_prod)), "See separate production-bugs PDF; active production risks are listed first."],
        ["New / Open issues", str(status_counts["New / Open"]), "Triage and plan."],
        ["In Progress issues", str(status_counts["In Progress"]), "Continue development and confirm next milestones."],
        ["Ready for Testing", str(status_counts["Ready for Testing"]), "Complete QA validation."],
        ["Unassigned active issues", str(len(unassigned_active)), "Assign owners; see Active Issues detail."],
    ], [180, 80, 400], font_size=8.2))
    story += [Spacer(1, 7), section_bar("4. Release / Deployment Updates", width - 2 * margin), Spacer(1, 3)]
    deployment_done = sum(r["Status"] == "Done" for r in deployment)
    story.append(table([
        ["Metric", "Count", "Notes"],
        ["Deployment-tagged issues", str(len(deployment)), "Includes release and deployment work."],
        ["Deployment-tagged Done", str(deployment_done), "Completed deployment items in the extract."],
        ["Deployment-tagged still open", str(len(deployment) - deployment_done), "Follow up on remaining deployment work."],
        ["QA automation still open", str(len(qa_auto_open)), "Regression items not yet Done."],
    ], [180, 80, 400], font_size=8.2))
    story += [Spacer(1, 7), section_bar("5. Next Week's Focus", width - 2 * margin), Spacer(1, 3)]
    story.append(table([
        ["Focus area", "Recommended action", "Basis"],
        ["Production defects", "Prioritize active production bugs and confirm ownership.", f"{len(active_prod)} active production bugs"],
        ["Testing pipeline", "Close or retest items currently Ready for Testing.", f"{status_counts['Ready for Testing']} Ready for Testing"],
        ["Open backlog", "Triage New / Open items and assign unowned work.", f"{status_counts['New / Open']} New / Open; {len(unassigned_active)} unassigned active issues"],
    ], [150, 320, 190], font_size=8.2))
    story += [Spacer(1, 7), p("Source note: The CSV contains issue status, ownership, labels, and production-bug flags, but no issue dates, estimates, due dates, or sprint timestamps. Counts reflect the supplied Sprint 101 extract rather than a dated weekly delta.", FOOTER)]

    story += [PageBreak(), p("ACTIVE ISSUES", TITLE), p("All records with Status other than Done, sorted with production bugs first.", SUBTITLE)]
    active_sorted = sorted(active, key=lambda r: (0 if r["Production Bug"] == "Yes" else 1, STATUS_ORDER.get(r["Status"], 99), r["Key"]))
    active_rows = [["Key", "Summary", "Issue Type", "Assignee", "Status", "Labels", "Attention", "Next Step"]]
    for r in active_sorted:
        active_rows.append([
            r["Key"], r["Summary"], r["Issue Type"], r["Assignee"] or "Unassigned", r["Status"], r["Labels"],
            "Production risk" if r["Production Bug"] == "Yes" else ("Owner needed" if not r["Assignee"] else r["Status"]), next_step(r)
        ])
    story.append(table(active_rows, [62, 240, 58, 85, 78, 112, 78, 100], font_size=6.8, status_col=4))
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    doc.build(story, onFirstPage=footer, onLaterPages=footer)


def build_production_pdf(records):
    width, height = landscape(A4)
    margin = 14 * mm
    doc = SimpleDocTemplate(PROD_PDF, pagesize=landscape(A4), leftMargin=margin, rightMargin=margin, topMargin=12 * mm, bottomMargin=18 * mm)
    production = [r for r in records if r["Production Bug"] == "Yes"]
    done = [r for r in production if r["Status"] == "Done"]
    active = [r for r in production if r["Status"] != "Done"]
    status_counts = Counter(r["Status"] for r in production)
    story = [
        p("PRODUCTION BUG REPORT", TITLE),
        p("Sprint 101 | Records flagged Production Bug = Yes | Source: sprint_101_status_updated.csv", SUBTITLE),
        table([
            ["Production bugs", str(len(production)), "Done", str(len(done)), "Still active", str(len(active)), "Overall status", "Amber"],
        ], [105, 55, 55, 45, 70, 55, 85, 55], header=False, font_size=8.2, row_bands=False),
        Spacer(1, 7),
        section_bar("Production Bug Status Summary", width - 2 * margin),
        Spacer(1, 3),
    ]
    status_rows = [["Status", "Count", "Recommended follow-up"]]
    followups = {
        "New / Open": "Triage and prioritize production fix",
        "In Progress": "Continue production fix",
        "Ready for Testing": "Complete production validation",
        "HerdX Accepted": "Confirm disposition and close",
        "Cannot Reproduce": "Confirm reproduction outcome",
        "Done": "No further action in this extract",
    }
    for status in ["New / Open", "In Progress", "Ready for Testing", "HerdX Accepted", "Cannot Reproduce", "Done"]:
        if status_counts[status]:
            status_rows.append([status, str(status_counts[status]), followups[status]])
    story.append(table(status_rows, [170, 70, 510], font_size=8.2, status_col=0))
    story += [Spacer(1, 7), section_bar("Production Bug Details", width - 2 * margin), Spacer(1, 3)]
    prod_sorted = sorted(production, key=lambda r: (0 if r["Status"] != "Done" else 1, STATUS_ORDER.get(r["Status"], 99), r["Key"]))
    detail_rows = [["Key", "Summary", "Issue Type", "Assignee", "Status", "Labels", "Next Step"]]
    for r in prod_sorted:
        detail_rows.append([
            r["Key"], r["Summary"], r["Issue Type"], r["Assignee"] or "Unassigned", r["Status"], r["Labels"], next_step(r)
        ])
    story.append(table(detail_rows, [62, 245, 58, 90, 80, 130, 120], font_size=7.0, status_col=4))
    story += [Spacer(1, 7), p("Source note: This report includes all 21 records flagged as production bugs in the supplied CSV. The source does not include issue dates, due dates, or resolution timestamps.", FOOTER)]
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    doc.build(story, onFirstPage=footer, onLaterPages=footer)


if __name__ == "__main__":
    all_records = parse_csv(CSV_PATH)
    build_full_pdf(all_records)
    build_production_pdf(all_records)
    print({"records": len(all_records), "production_bugs": sum(r["Production Bug"] == "Yes" for r in all_records), "full_pdf": FULL_PDF, "production_pdf": PROD_PDF})
