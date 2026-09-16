import csv
import os
import re
from difflib import SequenceMatcher

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph


CSV_PATH = r"C:\Users\PinkyAhmed\Downloads\Jira (2).csv"
OUTPUT_PATH = r"C:\work\jira-weekly-status-report\output\pdf\sprint_101_jira_engineering_wsr_product_backlog_format.pdf"

PAGE_W, PAGE_H = A4
MARGIN_X = 27
CONTENT_W = PAGE_W - 2 * MARGIN_X

NAVY = colors.HexColor("#1F4785")
GREEN = colors.HexColor("#0A993F")
BLUE = colors.HexColor("#2468C5")
RED = colors.HexColor("#ED1C24")
LIGHT_BLUE = colors.HexColor("#EAF3FD")
LIGHT_GREEN = colors.HexColor("#E8F6EC")
LIGHT_AMBER = colors.HexColor("#FFF1D2")
LIGHT_NAVY = colors.HexColor("#DCE7F4")
LIGHT_RED = colors.HexColor("#FFF0F0")
GRID = colors.HexColor("#B8C7D9")
ROW_ALT = colors.HexColor("#F7F9FB")
TEXT = colors.HexColor("#15335E")
MUTED = colors.HexColor("#52657A")


def ascii_clean(value):
    replacements = {
        "\u2013": "-", "\u2014": "-", "\u2011": "-",
        "\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"',
        "\ufffd": "-",
        "\u00a0": " ", "\u2003": " ", "\u200b": "", "\ufeff": "",
    }
    text = str(value or "")
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text.encode("ascii", "ignore").decode("ascii")


def parse_records(path):
    with open(path, "r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.reader(stream)
        header = next(reader)
        rows = list(reader)
    if "Issue key" in header:
        header_map = {}
        for index, value in enumerate(header):
            header_map.setdefault(value, []).append(index)
        summary_index = header_map["Summary"][0]
        key_index = header_map["Issue key"][0]
        type_index = header_map["Issue Type"][0]
        status_index = header_map["Status"][0]
        assignee_index = header_map["Assignee"][0]
        label_indexes = header_map.get("Labels", [])
        records = []
        for raw in rows:
            if not raw or not raw[key_index].strip():
                continue
            summary = raw[summary_index].strip()
            issue_type = raw[type_index].strip()
            labels = ",".join(raw[index].strip() for index in label_indexes if index < len(raw) and raw[index].strip())
            label_tokens = {value.strip().lower() for value in labels.split(",") if value.strip()}
            production_bug = "Yes" if issue_type == "Bug" and ("prod" in label_tokens or "production" in summary.lower()) else "No"
            records.append({
                "Key": raw[key_index].strip(),
                "Summary": summary,
                "Issue Type": issue_type,
                "Assignee": raw[assignee_index].strip(),
                "Status": raw[status_index].strip(),
                "Labels": labels,
                "Production Bug": production_bug,
            })
        return records
    records = []
    for raw in rows:
        if not raw or not raw[0].strip():
            continue
        type_index = next(i for i, value in enumerate(raw[1:], 1) if value.strip() in types)
        records.append({
            "Key": raw[0].strip(),
            "Summary": ",".join(raw[1:type_index]).strip(),
            "Issue Type": raw[type_index].strip(),
            "Assignee": (raw[type_index + 1] if len(raw) > type_index + 1 else "").strip(),
            "Status": (raw[type_index + 2] if len(raw) > type_index + 2 else "").strip(),
            "Labels": ",".join(raw[type_index + 3:-1]).strip(),
            "Production Bug": raw[-1].strip(),
        })
    return records


def issue_number(key):
    match = re.search(r"(\d+)$", key)
    return int(match.group(1)) if match else 0


STOPWORDS = {
    "the", "and", "for", "with", "from", "into", "when", "after", "this", "that", "are", "not",
    "task", "dev", "qa", "prod", "production", "staging", "release", "page", "issue", "activity",
    "log", "session", "show", "display", "displayed", "implement", "functionality", "task", "bug",
}


def tokens(text):
    text = ascii_clean(text).lower()
    text = re.sub(r"[^a-z0-9 ]+", " ", text)
    return {word for word in text.split() if len(word) > 2 and word not in STOPWORDS}


def normalized_summary(text):
    text = ascii_clean(text).lower()
    prefixes = [
        r"^dev\s+task\s*[-:]\s*", r"^qa\s+task\s*[-:]\s*", r"^activity\s+log\s+(dev|qa)\s+task\s*[-:]\s*",
        r"^dashboard\s+qa\s+task\s*[-:]\s*", r"^report\s+qa\s+task\s*[-:]\s*", r"^prod\s+issue\s*[-:]\s*",
        r"^prod\s*[-:]\s*", r"^production\s*[-:]\s*", r"^qa\s+task\s*[-:]\s*", r"^code\s+review\s*[-:]\s*",
    ]
    for prefix in prefixes:
        text = re.sub(prefix, "", text).strip()
    return text


def related_items(workstream, candidates):
    base = tokens(normalized_summary(workstream["Summary"]))
    base_text = normalized_summary(workstream["Summary"])
    matches = []
    for candidate in candidates:
        candidate_tokens = tokens(normalized_summary(candidate["Summary"]))
        candidate_text = normalized_summary(candidate["Summary"])
        if not base or not candidate_tokens:
            continue
        common = len(base & candidate_tokens)
        jaccard = common / max(1, len(base | candidate_tokens))
        sequence = SequenceMatcher(None, base_text, candidate_text).ratio()
        phrase_match = base_text in candidate_text or candidate_text in base_text
        if phrase_match or sequence >= 0.78 or (common >= 3 and jaccard >= 0.45):
            matches.append(candidate)
    return matches


def task_status_text(items):
    if not items:
        return "-"
    done = sum(item["Status"] == "Done" for item in items)
    if done == len(items):
        return f"{done} / {len(items)} Done"
    counts = []
    if done:
        counts.append(f"{done} / {len(items)} Done")
    for status in ["In Progress", "New / Open", "Ready for Testing", "HerdX Accepted"]:
        count = sum(item["Status"] == status for item in items)
        if count:
            counts.append(f"{count} {status}")
    return " + ".join(counts)


def bug_status_text(items):
    if not items:
        return "-"
    open_count = sum(item["Status"] != "Done" for item in items)
    return f"{open_count} Open" if open_count else "0 Open"


def notes_text(tasks, bugs):
    if not tasks and not bugs:
        return "No linked items"
    active_tasks = sum(item["Status"] != "Done" for item in tasks)
    active_bugs = sum(item["Status"] != "Done" for item in bugs)
    notes = []
    if tasks and active_tasks == 0:
        notes.append("All tasks done")
    elif active_tasks:
        notes.append(f"{active_tasks} task(s) in progress")
    if active_bugs:
        notes.append(f"{active_bugs} open bug(s)")
    return "; ".join(notes) if notes else "All linked items done"


def make_workstreams(records):
    workstreams = [r for r in records if r["Issue Type"] in {"Story", "Improvement"}]
    tasks = [r for r in records if r["Issue Type"] == "Task"]
    bugs = [r for r in records if r["Issue Type"] == "Bug"]
    workstreams.sort(key=lambda r: issue_number(r["Key"]), reverse=True)
    prepared = []
    for workstream in workstreams:
        linked_tasks = related_items(workstream, tasks)
        linked_bugs = related_items(workstream, bugs)
        prepared.append({
            "record": workstream,
            "tasks": linked_tasks,
            "bugs": linked_bugs,
            "task_status": task_status_text(linked_tasks),
            "bug_status": bug_status_text(linked_bugs),
            "notes": notes_text(linked_tasks, linked_bugs),
        })
    return prepared


def paragraph(text, size=5.6, leading=6.6, color=TEXT, bold=False, align=TA_LEFT):
    style = ParagraphStyle(
        name=f"p{size}{leading}{bold}{align}", fontName="Helvetica-Bold" if bold else "Helvetica",
        fontSize=size, leading=leading, textColor=color, alignment=align,
    )
    safe = ascii_clean(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return Paragraph(safe, style)


def draw_paragraph(c, text, x, top_y, width, height, size=5.6, leading=6.6, color=TEXT, bold=False, align=TA_LEFT):
    para = paragraph(text, size, leading, color, bold, align)
    w, h = para.wrap(width, height)
    para.drawOn(c, x, top_y - h - 1)
    return h


def draw_kpi(c, x, top_y, width, value, label, fill, border):
    value_h = 34
    label_h = 23
    c.setFillColor(fill)
    c.setStrokeColor(fill)
    c.rect(x, top_y - value_h, width, value_h, fill=1, stroke=1)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(x + width / 2, top_y - 23, ascii_clean(value))
    c.setFillColor(colors.white)
    c.setStrokeColor(border)
    c.setLineWidth(0.7)
    c.rect(x, top_y - value_h - label_h - 5, width, label_h, fill=0, stroke=1)
    c.setFillColor(border)
    c.setFont("Helvetica-Bold", 6.8)
    c.drawCentredString(x + width / 2, top_y - value_h - 19, ascii_clean(label).upper())


def draw_banner(c, y, text):
    h = 44
    c.setFillColor(RED)
    c.rect(MARGIN_X, y, CONTENT_W, h, fill=1, stroke=0)
    c.setFillColor(LIGHT_RED)
    c.rect(MARGIN_X + 44, y, CONTENT_W - 44, h, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 20)
    c.drawCentredString(MARGIN_X + 22, y + 14, "!")
    draw_paragraph(c, text, MARGIN_X + 51, y + h - 8, CONTENT_W - 62, h - 10, size=6.8, leading=8.3, color=RED, bold=True)


def draw_info_card(c, x, y, width, height, title, bullets):
    c.setStrokeColor(GRID)
    c.setLineWidth(0.6)
    c.rect(x, y, width, height, fill=0, stroke=1)
    c.setFillColor(colors.HexColor("#F3F5F7"))
    c.rect(x + 8, y + height - 27, width - 16, 22, fill=1, stroke=0)
    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 8.6)
    c.drawCentredString(x + width / 2, y + height - 20, title.upper())
    cursor = y + height - 41
    for bullet in bullets:
        h = draw_paragraph(c, "- " + bullet, x + 10, cursor, width - 20, 20, size=6.5, leading=8.0, color=TEXT)
        cursor -= max(12, h + 2)


def status_style(status):
    if status == "In Progress":
        return LIGHT_AMBER, colors.HexColor("#C47F00")
    if status == "Ready for Testing":
        return LIGHT_BLUE, BLUE
    if status == "HerdX Accepted":
        return LIGHT_NAVY, NAVY
    if status == "Done":
        return LIGHT_GREEN, GREEN
    if status in {"Cannot Reproduce", "Rejected / Not a Bug", "Discarded"}:
        return LIGHT_RED, RED
    return LIGHT_BLUE, BLUE


def draw_snapshot_table(c, rows, start_index, end_index, top_y, page_number):
    col_widths = [18, 204, 62, 68, 63, 62, 65]
    x0 = MARGIN_X
    header_h = 18
    row_h = 20
    c.setFillColor(NAVY)
    c.rect(x0, top_y - header_h, sum(col_widths), header_h, fill=1, stroke=0)
    headers = ["#", "USER STORY / WORKSTREAM", "STATUS", "TASK STATUS", "BUG STATUS", "OWNER", "NOTES"]
    x = x0
    for idx, header in enumerate(headers):
        draw_paragraph(c, header, x + 2, top_y - 4, col_widths[idx] - 4, header_h - 3, size=5.7, leading=6.3, color=colors.white, bold=True, align=1)
        if idx > 0:
            c.setStrokeColor(colors.white)
            c.setLineWidth(0.35)
            c.line(x, top_y - header_h, x, top_y)
        x += col_widths[idx]
    current_y = top_y - header_h
    for number, prepared in enumerate(rows[start_index:end_index], start=start_index + 1):
        data = prepared["record"]
        fill = ROW_ALT if number % 2 == 0 else colors.white
        c.setFillColor(fill)
        c.setStrokeColor(GRID)
        c.setLineWidth(0.45)
        c.rect(x0, current_y - row_h, sum(col_widths), row_h, fill=1, stroke=1)
        values = [
            str(number),
            f"{data['Key']} - {data['Summary']}",
            data["Status"],
            prepared["task_status"],
            prepared["bug_status"],
            data["Assignee"] or "-",
            prepared["notes"],
        ]
        x = x0
        for idx, value in enumerate(values):
            if idx in {2, 3, 4}:
                cell_fill, cell_text = status_style(data["Status"] if idx == 2 else ("Done" if "Done" in value and "Open" not in value else ("In Progress" if "in progress" in value else "New / Open")))
                c.setFillColor(cell_fill)
                c.rect(x, current_y - row_h, col_widths[idx], row_h, fill=1, stroke=0)
                text_color = cell_text
            else:
                text_color = TEXT
            draw_paragraph(c, value, x + 2, current_y - 3, col_widths[idx] - 4, row_h - 3, size=5.0 if idx != 0 else 5.2, leading=5.9, color=text_color, bold=(idx == 5))
            if idx > 0:
                c.setStrokeColor(GRID)
                c.setLineWidth(0.35)
                c.line(x, current_y - row_h, x, current_y)
            x += col_widths[idx]
        current_y -= row_h
    return current_y


def linked_text(prepared):
    items = []
    for item in prepared["tasks"] + prepared["bugs"]:
        items.append(f"{item['Key']} - {item['Issue Type']} - {item['Summary']} - {item['Status']}")
    return " | ".join(items) if items else "No linked tasks / bugs in Jira export"


def draw_detail_table(c, rows, start_index, top_y, page_number):
    col_widths = [18, 204, 320]
    x0 = MARGIN_X
    header_h = 18
    row_y = top_y - header_h
    c.setFillColor(NAVY)
    c.rect(x0, row_y, sum(col_widths), header_h, fill=1, stroke=0)
    headers = ["#", "USER STORY / WORKSTREAM", "LINKED TASKS / BUGS - CURRENT STATUS"]
    x = x0
    for idx, header in enumerate(headers):
        draw_paragraph(c, header, x + 2, top_y - 4, col_widths[idx] - 4, header_h - 3, size=5.7, leading=6.3, color=colors.white, bold=True, align=1)
        if idx > 0:
            c.setStrokeColor(colors.white)
            c.setLineWidth(0.35)
            c.line(x, row_y, x, top_y)
        x += col_widths[idx]
    current_y = row_y
    index = start_index
    bottom = 39
    while index < len(rows):
        prepared = rows[index]
        data = prepared["record"]
        left = f"{data['Key']} - {data['Summary']}"
        right = linked_text(prepared)
        left_para = paragraph(left, 5.5, 6.5, NAVY)
        right_para = paragraph(right, 5.35, 6.35, TEXT)
        _, left_h = left_para.wrap(col_widths[1] - 8, 1000)
        _, right_h = right_para.wrap(col_widths[2] - 8, 1000)
        row_h = max(20, min(55, max(left_h, right_h) + 7))
        if current_y - row_h < bottom:
            break
        fill = ROW_ALT if (index + 1) % 2 == 0 else colors.white
        c.setFillColor(fill)
        c.setStrokeColor(GRID)
        c.setLineWidth(0.45)
        c.rect(x0, current_y - row_h, sum(col_widths), row_h, fill=1, stroke=1)
        left_para.drawOn(c, x0 + col_widths[0] + 4, current_y - left_h - 4)
        right_para.drawOn(c, x0 + col_widths[0] + col_widths[1] + 4, current_y - right_h - 4)
        c.setFont("Helvetica-Bold", 5.5)
        c.setFillColor(NAVY)
        c.drawCentredString(x0 + col_widths[0] / 2, current_y - 12, str(index + 1))
        c.setStrokeColor(GRID)
        c.line(x0 + col_widths[0], current_y - row_h, x0 + col_widths[0], current_y)
        c.line(x0 + col_widths[0] + col_widths[1], current_y - row_h, x0 + col_widths[0] + col_widths[1], current_y)
        current_y -= row_h
        index += 1
    return index, current_y


def footer(c, page_number):
    c.setFillColor(NAVY)
    c.setFont("Helvetica", 7.2)
    c.drawRightString(PAGE_W - MARGIN_X, 22, f"Page {page_number}")


def main():
    records = parse_records(CSV_PATH)
    workstreams = make_workstreams(records)
    stories = [r for r in records if r["Issue Type"] == "Story"]
    tasks = [r for r in records if r["Issue Type"] == "Task"]
    bugs = [r for r in records if r["Issue Type"] == "Bug"]
    in_progress = sum(r["record"]["Status"] == "In Progress" for r in workstreams)
    task_done = sum(r["Status"] == "Done" for r in tasks)
    open_bugs = sum(r["Status"] != "Done" for r in bugs)
    active_records = [r for r in records if r["Status"] != "Done"]
    active_production = [r for r in active_records if r["Production Bug"] == "Yes"]
    unassigned_active = sum(not r["Assignee"] for r in active_records)
    ready_for_testing = sum(r["Status"] == "Ready for Testing" for r in records)
    deployment_open = sum("deployment" in r["Labels"].lower() and r["Status"] != "Done" for r in records)

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    c = canvas.Canvas(OUTPUT_PATH, pagesize=A4)
    c.setTitle("Sprint 101 Weekly Status Report")

    # Page 1: match the reference cover and snapshot layout.
    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(PAGE_W / 2, 807, "WEEKLY STATUS REPORT")
    c.setFont("Helvetica-Bold", 8.2)
    c.setFillColor(colors.HexColor("#1D2D45"))
    c.drawCentredString(PAGE_W / 2, 793, "Sprint 101 | Week of 31 Aug-4 Sep 2026")

    card_gap = 9
    card_w = (CONTENT_W - 3 * card_gap) / 4
    card_y = 763
    cards = [
        (str(len(workstreams)), "USER STORIES / WORKSTREAMS", NAVY, NAVY),
        (str(in_progress), "IN PROGRESS", GREEN, GREEN),
        (f"{task_done}/{len(tasks)}", "RELATED TASKS DONE", BLUE, BLUE),
        (str(open_bugs), "OPEN RELATED BUGS", RED, RED),
    ]
    for idx, (value, label, fill, border) in enumerate(cards):
        draw_kpi(c, MARGIN_X + idx * (card_w + card_gap), card_y, card_w, value, label, fill, border)

    draw_banner(c, 650, f"OVERALL STATUS: AT RISK  {in_progress} of {len(workstreams)} workstreams are in progress | {task_done}/{len(tasks)} related tasks done | {open_bugs} related bugs are open and require closure/verification.")

    info_y = 546
    info_h = 104
    info_gap = 14
    info_w = (CONTENT_W - 2 * info_gap) / 3
    draw_info_card(c, MARGIN_X, info_y, info_w, info_h, "Key Highlights", [
        f"{in_progress} of {len(workstreams)} workstreams are in progress.",
        f"{task_done} of {len(tasks)} tasks are completed.",
        f"{open_bugs} bugs remain open.",
        f"{len(active_production)} active production bugs require follow-up.",
    ])
    draw_info_card(c, MARGIN_X + info_w + info_gap, info_y, info_w, info_h, "Next Focus", [
        f"Close or validate the {ready_for_testing} items Ready for Testing.",
        f"Prioritize the {len(active_production)} active production bugs.",
        f"Triage New / Open work and assign owners.",
        f"Follow up on {deployment_open} open deployment items.",
    ])
    draw_info_card(c, MARGIN_X + 2 * (info_w + info_gap), info_y, info_w, info_h, "Management Attention", [
        f"Review {unassigned_active} unassigned active items.",
        "Track high-priority production work closely.",
        "Confirm closure or next action for accepted items.",
        "Source extract has no due dates or estimates.",
    ])

    title_y = 527
    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 8.8)
    c.drawString(MARGIN_X + 6, title_y, f"SPRINT 101 - USER STORY / WORKSTREAM SNAPSHOT (ALL {len(workstreams)} ITEMS)")
    draw_snapshot_table(c, workstreams, 0, min(22, len(workstreams)), 512, 1)
    footer(c, 1)
    c.showPage()

    # Page 2: remaining snapshot rows, matching the reference continuation.
    draw_snapshot_table(c, workstreams, min(22, len(workstreams)), len(workstreams), 808, 2)
    footer(c, 2)
    c.showPage()

    # Pages 3 onward: detailed delivery status in the reference's two-column format.
    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(MARGIN_X + 6, 812, "DETAILED DELIVERY STATUS (User Story    Tasks / Bugs)")
    next_index, _ = draw_detail_table(c, workstreams, 0, 794, 3)
    footer(c, 3)
    c.showPage()
    page_number = 4
    while next_index < len(workstreams):
        next_index, _ = draw_detail_table(c, workstreams, next_index, 815, page_number)
        footer(c, page_number)
        c.showPage()
        page_number += 1
    c.save()
    print({"output": OUTPUT_PATH, "records": len(records), "workstreams": len(workstreams), "pages": page_number - 1})


if __name__ == "__main__":
    main()
