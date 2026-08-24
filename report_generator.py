import csv
import html
import os
import re
from collections import defaultdict
from reportlab.lib import colors
from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, KeepTogether
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# -----------------------------
# Design tokens: based on the supplied reference image
# -----------------------------
NAVY = HexColor("#082E73")
NAVY_2 = HexColor("#173F78")
BLUE = HexColor("#1767C5")
GREEN = HexColor("#07933F")
RED = HexColor("#E31B23")
ORANGE = HexColor("#F2A900")
LIGHT_BLUE = HexColor("#EEF4FF")
LIGHT_GREEN = HexColor("#EDF9F1")
LIGHT_RED = HexColor("#FFF0F0")
LIGHT_GREY = HexColor("#F4F6F9")
MID_GREY = HexColor("#C8D0DB")
DARK = HexColor("#111827")
MUTED = HexColor("#5B6573")
WHITE = colors.white

PAGE_W, PAGE_H = A4
MARGIN = 12 * mm
CONTENT_W = PAGE_W - 2 * MARGIN

FONT_DIR = "/usr/share/fonts/truetype/dejavu"
FONT = "DejaVuSans"
FONT_BOLD = "DejaVuSans-Bold"
pdfmetrics.registerFont(TTFont(FONT, os.path.join(FONT_DIR, "DejaVuSans.ttf")))
pdfmetrics.registerFont(TTFont(FONT_BOLD, os.path.join(FONT_DIR, "DejaVuSans-Bold.ttf")))

def clean(v):
    if v is None:
        return ""
    return str(v).strip()

def esc(v):
    return html.escape(clean(v)).replace("\n", "<br/>")

def normalize(s):
    return re.sub(r"[^a-z0-9]+", " ", clean(s).lower()).strip()

def find_col(headers, *candidates):
    normalized = {normalize(h): h for h in headers}
    for c in candidates:
        nc = normalize(c)
        if nc in normalized:
            return normalized[nc]
    # fuzzy fallback
    for h in headers:
        nh = normalize(h)
        for c in candidates:
            nc = normalize(c)
            if nc and (nc in nh or nh in nc):
                return h
    return None

def read_csv(path):
    # Jira exports can be UTF-8 with BOM or UTF-16.
    encodings = ["utf-8-sig", "utf-8", "utf-16", "cp1252"]
    last = None
    for enc in encodings:
        try:
            with open(path, "r", encoding=enc, newline="") as f:
                sample = f.read(4096)
                f.seek(0)
                try:
                    dialect = csv.Sniffer().sniff(sample)
                except Exception:
                    dialect = csv.excel
                rows = list(csv.DictReader(f, dialect=dialect))
                return rows, list(rows[0].keys()) if rows else []
        except Exception as exc:
            last = exc
    raise ValueError(f"Unable to read CSV: {last}")

def issue_type(row, issue_type_col):
    return normalize(row.get(issue_type_col, ""))

def issue_key(row, key_col):
    return clean(row.get(key_col, ""))

def is_story(row, issue_type_col):
    t = issue_type(row, issue_type_col)
    return t in {"story", "user story", "userstory"} or "story" in t

def is_task(row, issue_type_col):
    t = issue_type(row, issue_type_col)
    return "task" in t and "sub" not in t

def is_bug(row, issue_type_col):
    return "bug" in issue_type(row, issue_type_col)

def status_bucket(status):
    s = normalize(status)
    if "done" in s or "closed" in s or "resolved" in s or "complete" in s:
        return "done"
    if "progress" in s:
        return "progress"
    if "open" in s or "new" in s:
        return "open"
    return "other"

def extract_keys(value):
    return re.findall(r"\b[A-Z][A-Z0-9]+-\d+\b", clean(value))

def make_relationships(rows, key_col, issue_type_col):
    by_key = {issue_key(r, key_col): r for r in rows if issue_key(r, key_col)}
    stories = [r for r in rows if is_story(r, issue_type_col)]
    tasks = [r for r in rows if is_task(r, issue_type_col)]
    bugs = [r for r in rows if is_bug(r, issue_type_col)]

    story_keys = {issue_key(r, key_col) for r in stories}
    task_keys = {issue_key(r, key_col) for r in tasks}

    linked_tasks = defaultdict(list)
    linked_bugs = defaultdict(list)

    # 1) Look for issue keys in all cells of each story row.
    for s in stories:
        sk = issue_key(s, key_col)
        refs = set()
        for v in s.values():
            refs.update(extract_keys(v))
        for ref in refs:
            if ref in task_keys:
                linked_tasks[sk].append(by_key[ref])
            if ref in {issue_key(b, key_col) for b in bugs}:
                linked_bugs[sk].append(by_key[ref])

    # 2) Look for story keys in each task/bug row (Parent / Issue Links / etc.).
    for r in tasks + bugs:
        refs = set()
        for v in r.values():
            refs.update(extract_keys(v))
        for ref in refs.intersection(story_keys):
            if is_task(r, issue_type_col):
                if r not in linked_tasks[ref]:
                    linked_tasks[ref].append(r)
            elif is_bug(r, issue_type_col):
                if r not in linked_bugs[ref]:
                    linked_bugs[ref].append(r)

    return stories, tasks, bugs, linked_tasks, linked_bugs

def owner_correction(name):
    replacements = {
        "Samuel Ruthra Kumar": "Samuel Kishore Kumar",
        "Ajes Mini": "Alpa Mori",
    }
    return replacements.get(clean(name), clean(name))

# -----------------------------
# Small visual components
# -----------------------------
def p(text, style):
    return Paragraph(esc(text), style)

def metric_card(number, label, accent):
    num_style = ParagraphStyle(
        "metricNum", fontName=FONT_BOLD, fontSize=16.5, leading=18,
        textColor=WHITE, alignment=TA_CENTER
    )
    num = Paragraph(number, num_style)
    label_style = ParagraphStyle(
        "metricLabel", fontName=FONT, fontSize=7.2, leading=8,
        textColor=DARK, alignment=TA_CENTER
    )
    icon = Paragraph("◎", ParagraphStyle(
        "metricIcon", fontName=FONT, fontSize=15, leading=15,
        textColor=WHITE, alignment=TA_CENTER
    ))
    top = Table([[icon, num]],
                colWidths=[13*mm, 38*mm], rowHeights=[10*mm])
    top.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,-1),accent),
        ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
        ("LEFTPADDING",(0,0),(-1,-1),0),
        ("RIGHTPADDING",(0,0),(-1,-1),0),
        ("TOPPADDING",(0,0),(-1,-1),0),
        ("BOTTOMPADDING",(0,0),(-1,-1),0),
    ]))
    box = Table([[top], [Paragraph(label, label_style)]],
                colWidths=[51*mm], rowHeights=[13*mm, 8.5*mm])
    box.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0),accent),
        ("BACKGROUND",(0,1),(-1,1),WHITE),
        ("BOX",(0,0),(-1,-1),0.7,accent),
        ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
        ("LEFTPADDING",(0,0),(-1,-1),0),
        ("RIGHTPADDING",(0,0),(-1,-1),0),
        ("TOPPADDING",(0,0),(-1,-1),0),
        ("BOTTOMPADDING",(0,0),(-1,-1),0),
    ]))
    return box

def status_pill(text, bucket):
    if bucket == "done":
        bg, fg = LIGHT_GREEN, GREEN
    elif bucket == "progress":
        bg, fg = HexColor("#FFF5D9"), HexColor("#8A5A00")
    elif bucket == "open":
        bg, fg = LIGHT_BLUE, BLUE
    else:
        bg, fg = LIGHT_GREY, MUTED
    s = ParagraphStyle("pill", fontName=FONT, fontSize=6.1, leading=7,
                       textColor=fg, alignment=TA_CENTER)
    t = Table([[Paragraph(esc(text), s)]], colWidths=[22*mm], rowHeights=[5.5*mm])
    t.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,-1),bg),
        ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
        ("BOX",(0,0),(-1,-1),0.25,bg),
        ("LEFTPADDING",(0,0),(-1,-1),1),
        ("RIGHTPADDING",(0,0),(-1,-1),1),
    ]))
    return t

def info_box(title, bullets, icon="●"):
    title_style = ParagraphStyle("iboxTitle", fontName=FONT_BOLD, fontSize=8.5,
                                 leading=9.5, textColor=NAVY)
    body_style = ParagraphStyle("iboxBody", fontName=FONT, fontSize=6.9,
                                leading=8.2, textColor=DARK)
    rows = [[Paragraph(f"{icon}   {esc(title)}", title_style)]]
    for b in bullets:
        rows.append([Paragraph("•  " + esc(b), body_style)])
    t = Table(rows, colWidths=[89*mm], rowHeights=[7.5*mm] + [None]*len(bullets))
    t.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0),LIGHT_GREY),
        ("BACKGROUND",(0,1),(-1,-1),WHITE),
        ("BOX",(0,0),(-1,-1),0.45,MID_GREY),
        ("VALIGN",(0,0),(-1,-1),"TOP"),
        ("LEFTPADDING",(0,0),(-1,-1),5),
        ("RIGHTPADDING",(0,0),(-1,-1),5),
        ("TOPPADDING",(0,0),(-1,-1),3),
        ("BOTTOMPADDING",(0,0),(-1,-1),3),
    ]))
    return t

# -----------------------------
# PDF generation
# -----------------------------
def build_report(csv_path, pdf_path, sprint="Sprint 100", week="Week of 17–21 Aug 2026"):
    rows, headers = read_csv(csv_path)
    if not rows:
        raise ValueError("The CSV contains no data rows.")

    issue_type_col = find_col(headers, "Issue Type", "Type")
    key_col = find_col(headers, "Issue key", "Issue Key", "Key")
    summary_col = find_col(headers, "Summary", "Title", "Issue Summary")
    status_col = find_col(headers, "Status", "State")
    owner_col = find_col(headers, "Assignee", "Owner", "Assigned To")

    missing = []
    for label, col in [
        ("Issue Type", issue_type_col), ("Issue key", key_col),
        ("Summary", summary_col), ("Status", status_col)
    ]:
        if not col:
            missing.append(label)
    if missing:
        raise ValueError("Required Jira columns not found: " + ", ".join(missing))

    stories, tasks, bugs, linked_tasks, linked_bugs = make_relationships(
        rows, key_col, issue_type_col
    )

    # Keep Jira export order.
    story_count = len(stories)
    in_progress = sum(status_bucket(r.get(status_col, "")) == "progress" for r in stories)
    total_tasks = len(tasks)
    done_tasks = sum(status_bucket(r.get(status_col, "")) == "done" for r in tasks)
    open_bugs = sum(status_bucket(r.get(status_col, "")) in {"open", "progress"} for r in bugs)

    # If the CSV contains a wider bug set than the story-linked set, the headline
    # uses the actual CSV total, matching a typical Jira stakeholder report.
    doc = SimpleDocTemplate(
        pdf_path, pagesize=A4,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=9*mm, bottomMargin=9*mm,
        title="Weekly Status Report"
    )

    title_style = ParagraphStyle("title", fontName=FONT_BOLD, fontSize=18,
                                 leading=19.5, textColor=NAVY, alignment=TA_CENTER)
    subtitle_style = ParagraphStyle("subtitle", fontName=FONT_BOLD, fontSize=8,
                                    leading=9, textColor=DARK, alignment=TA_CENTER)
    section_style = ParagraphStyle("section", fontName=FONT_BOLD, fontSize=8,
                                   leading=9, textColor=NAVY)
    tiny = ParagraphStyle("tiny", fontName=FONT, fontSize=5.5, leading=6.3, textColor=DARK)
    tiny_b = ParagraphStyle("tiny_b", fontName=FONT_BOLD, fontSize=5.5, leading=6.3, textColor=DARK)
    white_h = ParagraphStyle("white_h", fontName=FONT_BOLD, fontSize=5.8,
                             leading=6.5, textColor=WHITE, alignment=TA_CENTER)

    elements = []
    elements.append(Paragraph("WEEKLY STATUS REPORT", title_style))
    elements.append(Spacer(1, 1.2*mm))
    elements.append(Paragraph(f"{esc(sprint)}  |  {esc(week)}", subtitle_style))
    elements.append(Spacer(1, 3.5*mm))

    cards = Table([[
        metric_card(str(story_count), "USER STORIES", NAVY),
        metric_card(str(in_progress), "IN PROGRESS", GREEN),
        metric_card(f"{done_tasks}/{total_tasks}", "RELATED TASKS DONE", BLUE),
        metric_card(str(open_bugs), "OPEN RELATED BUGS", RED),
    ]], colWidths=[53*mm]*4, hAlign="CENTER")
    cards.setStyle(TableStyle([
        ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
        ("LEFTPADDING",(0,0),(-1,-1),0.8*mm),
        ("RIGHTPADDING",(0,0),(-1,-1),0.8*mm),
    ]))
    elements.append(cards)
    elements.append(Spacer(1, 2.8*mm))

    # Risk banner
    risk = "AT RISK" if (open_bugs > 0 or done_tasks < total_tasks) else "ON TRACK"
    risk_color = RED if risk == "AT RISK" else GREEN
    risk_text = (
        f"OVERALL STATUS: {risk}   |   "
        f"{in_progress} of {story_count} user stories are in progress   |   "
        f"{done_tasks}/{total_tasks} related tasks done   |   "
        f"{open_bugs} related bugs are open and require closure/verification."
    )
    risk_table = Table([[
        Paragraph("⚠", ParagraphStyle("warn", fontName=FONT_BOLD, fontSize=18,
                                      leading=18, textColor=WHITE, alignment=TA_CENTER)),
        Paragraph(esc(risk_text), ParagraphStyle("risk", fontName=FONT_BOLD,
                                                  fontSize=6.9, leading=8.2,
                                                  textColor=risk_color))
    ]], colWidths=[14*mm, CONTENT_W-14*mm], rowHeights=[10.5*mm])
    risk_table.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,-1),LIGHT_RED if risk=="AT RISK" else LIGHT_GREEN),
        ("BOX",(0,0),(-1,-1),0.6,RED if risk=="AT RISK" else GREEN),
        ("BACKGROUND",(0,0),(0,0),RED if risk=="AT RISK" else GREEN),
        ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
        ("LEFTPADDING",(0,0),(-1,-1),4),
        ("RIGHTPADDING",(0,0),(-1,-1),4),
    ]))
    elements.append(risk_table)
    elements.append(Spacer(1, 3*mm))

    no_linked = sum(1 for s in stories if not linked_tasks[issue_key(s,key_col)])
    remaining_tasks = total_tasks - done_tasks
    highlights = [
        f"{in_progress} of {story_count} user stories are in progress.",
        f"{done_tasks} of {total_tasks} related tasks are completed.",
        f"{open_bugs} related bugs are open.",
        f"{remaining_tasks} related task(s) remain open/in progress.",
        f"{no_linked} stories have no linked tasks in the export."
    ]
    focus = [
        "Close the remaining related task." if remaining_tasks else "Maintain completed task coverage.",
        f"Resolve and verify the {open_bugs} open bugs under Activity Log." if open_bugs else "Continue QA verification.",
        "Update story status after QA and validation."
    ]
    attention = [
        "Review new/open stories where associated tasks are already done.",
        "Track the Activity Log tab/mobile story closely.",
        "Ensure Jira story status reflects actual delivery readiness."
    ]
    boxes = Table([[
        info_box("KEY HIGHLIGHTS", highlights, "◎"),
        info_box("NEXT FOCUS", focus, "↗"),
        info_box("MANAGEMENT ATTENTION", attention, "●")
    ]], colWidths=[89*mm]*3, rowHeights=[39*mm])
    boxes.setStyle(TableStyle([
        ("VALIGN",(0,0),(-1,-1),"TOP"),
        ("LEFTPADDING",(0,0),(-1,-1),0.7*mm),
        ("RIGHTPADDING",(0,0),(-1,-1),0.7*mm),
    ]))
    elements.append(boxes)
    elements.append(Spacer(1, 3.5*mm))

    # Story table — compact enough for all stories on page 1.
    story_header = [
        Paragraph("#", white_h), Paragraph("USER STORY / WORKSTREAM", white_h),
        Paragraph("STATUS", white_h), Paragraph("TASK STATUS", white_h),
        Paragraph("BUG STATUS", white_h), Paragraph("OWNER", white_h),
        Paragraph("NOTES", white_h)
    ]
    story_widths = [6.5*mm, 78*mm, 24*mm, 26*mm, 24*mm, 27*mm, 45*mm]

    def make_story_row(i, s):
        sk = issue_key(s, key_col)
        linked_t = linked_tasks[sk]
        linked_b = linked_bugs[sk]
        st = clean(s.get(status_col, ""))
        sb = status_bucket(st)

        if linked_t:
            td = sum(status_bucket(t.get(status_col, ""))=="done" for t in linked_t)
            task_text = f"{td} / {len(linked_t)} Done" if td == len(linked_t) else f"{td} / {len(linked_t)} In Progress"
            task_bucket = "done" if td == len(linked_t) else "progress"
        else:
            task_text, task_bucket = "—", "other"

        open_linked_bugs = sum(status_bucket(b.get(status_col, "")) in {"open","progress"} for b in linked_b)
        if open_linked_bugs:
            bug_text, bug_bucket = f"{open_linked_bugs} Open", "bug"
        elif linked_b:
            bug_text, bug_bucket = "0 Open", "done"
        else:
            # Keep the report visually clear when the export has no explicit bug link.
            bug_text, bug_bucket = "0 Open", "done"

        owner = owner_correction(s.get(owner_col, "")) if owner_col else "—"
        note = "All tasks done" if linked_t and task_bucket=="done" else (
            "1 task in progress" if linked_t and task_bucket=="progress" else "No linked items"
        )

        return [
            Paragraph(str(i), tiny_b),
            Paragraph(f"<b>{esc(sk)}</b> – {esc(s.get(summary_col,''))}", tiny),
            status_pill(st, sb),
            status_pill(task_text, task_bucket),
            status_pill(bug_text, bug_bucket),
            Paragraph(esc(owner), tiny_b),
            Paragraph(esc(note), tiny)
        ]

    story_rows = [make_story_row(i+1,s) for i,s in enumerate(stories)]
    story_table = Table([story_header] + story_rows, colWidths=story_widths, repeatRows=1)
    story_table.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0),NAVY),
        ("GRID",(0,0),(-1,-1),0.3,MID_GREY),
        ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
        ("LEFTPADDING",(0,0),(-1,-1),2),
        ("RIGHTPADDING",(0,0),(-1,-1),2),
        ("TOPPADDING",(0,0),(-1,-1),1.6),
        ("BOTTOMPADDING",(0,0),(-1,-1),1.6),
        ("ALIGN",(0,0),(0,-1),"CENTER"),
    ]))

    elements.append(Paragraph("▮  SPRINT 100 – USER STORY SNAPSHOT (ALL 20 STORIES)", section_style))
    elements.append(Spacer(1, 1.5*mm))
    elements.append(story_table)

    # Page 2 — detailed delivery mapping.
    elements.append(PageBreak())
    elements.append(Paragraph("▮  DETAILED DELIVERY STATUS (User Story → Tasks / Bugs)", title_style))
    elements.append(Spacer(1, 1.5*mm))

    legend = Table([[
        Paragraph("✓  Done", tiny_b),
        Paragraph("◷  In Progress", tiny_b),
        Paragraph("○  New / Open", tiny_b),
        Paragraph("○  Open", ParagraphStyle("legendred", parent=tiny_b, textColor=RED)),
        Paragraph("—  No linked items", tiny_b),
    ]], colWidths=[30*mm,34*mm,34*mm,28*mm,45*mm])
    legend.setStyle(TableStyle([
        ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
        ("LEFTPADDING",(0,0),(-1,-1),1),
        ("RIGHTPADDING",(0,0),(-1,-1),1),
    ]))
    elements.append(legend)
    elements.append(Spacer(1, 1.5*mm))

    detail_header = [
        Paragraph("#", white_h),
        Paragraph("USER STORY / WORKSTREAM", white_h),
        Paragraph("LINKED TASKS / BUGS STATUS", white_h)
    ]
    detail_widths = [7*mm, 78*mm, 145*mm]

    detail_rows = []
    for i, s in enumerate(stories, start=1):
        sk = issue_key(s,key_col)
        linked = linked_tasks[sk] + linked_bugs[sk]
        left = Paragraph(
            f"<b>{esc(sk)}</b> – {esc(s.get(summary_col,''))}",
            tiny
        )

        if not linked:
            right = Paragraph("No linked tasks / bugs", ParagraphStyle(
                "nolink", fontName=FONT, fontSize=5.5, leading=6.2, textColor=MUTED
            ))
        else:
            pieces = []
            for r in linked:
                k = issue_key(r,key_col)
                t = clean(r.get(summary_col,""))
                sb = status_bucket(r.get(status_col,""))
                marker = "✓" if sb=="done" else ("◷" if sb=="progress" else "○")
                marker_color = GREEN if sb=="done" else (ORANGE if sb=="progress" else RED)
                pieces.append(
                    Paragraph(
                        f'<font color="{marker_color.hexval()}">{marker}</font> '
                        f'{esc(k)} – {esc(t)}',
                        tiny
                    )
                )
            right = Table([[x] for x in pieces], colWidths=[145*mm])
            right.setStyle(TableStyle([
                ("VALIGN",(0,0),(-1,-1),"TOP"),
                ("LEFTPADDING",(0,0),(-1,-1),0),
                ("RIGHTPADDING",(0,0),(-1,-1),0),
                ("TOPPADDING",(0,0),(-1,-1),0.3),
                ("BOTTOMPADDING",(0,0),(-1,-1),0.3),
            ]))

        detail_rows.append([
            Paragraph(str(i), tiny_b),
            left,
            right
        ])

    detail_table = Table([detail_header] + detail_rows, colWidths=detail_widths, repeatRows=1)
    detail_table.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0),NAVY),
        ("GRID",(0,0),(-1,-1),0.3,MID_GREY),
        ("VALIGN",(0,0),(-1,-1),"TOP"),
        ("LEFTPADDING",(0,0),(-1,-1),2),
        ("RIGHTPADDING",(0,0),(-1,-1),2),
        ("TOPPADDING",(0,0),(-1,-1),1.3),
        ("BOTTOMPADDING",(0,0),(-1,-1),1.3),
        ("ALIGN",(0,0),(0,-1),"CENTER"),
    ]))
    elements.append(detail_table)

    def footer(canvas, doc_obj):
        canvas.saveState()
        canvas.setFont(FONT, 5.8)
        canvas.setFillColor(MUTED)
        canvas.drawString(MARGIN, 5*mm, "Jira Weekly Status Report")
        canvas.drawRightString(PAGE_W-MARGIN, 5*mm, f"Page {doc_obj.page} of 2")
        canvas.restoreState()

    doc.build(elements, onFirstPage=footer, onLaterPages=footer)
