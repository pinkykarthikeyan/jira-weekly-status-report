import csv
import html
import os
from collections import Counter
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph


CSV_PATH = r"C:\Users\PinkyAhmed\Downloads\sprint102_workitems.csv"
OUTPUT_PATH = r"C:\work\jira-weekly-status-report\output\pdf\Sprint_102_WSR.pdf"

PAGE_W, PAGE_H = A4
MARGIN_X = 27
CONTENT_W = PAGE_W - 2 * MARGIN_X

NAVY = colors.HexColor("#244C86")
GREEN = colors.HexColor("#0A993F")
BLUE = colors.HexColor("#2468C5")
RED = colors.HexColor("#ED1C24")
AMBER = colors.HexColor("#C47F00")
LIGHT_BLUE = colors.HexColor("#EAF3FD")
LIGHT_GREEN = colors.HexColor("#E8F6EC")
LIGHT_AMBER = colors.HexColor("#FFF1D2")
LIGHT_NAVY = colors.HexColor("#DCE7F4")
LIGHT_RED = colors.HexColor("#FFF0F0")
GRID = colors.HexColor("#B8C7D9")
ROW_ALT = colors.HexColor("#F7F9FB")
TEXT = colors.HexColor("#15335E")
MUTED = colors.HexColor("#5E718E")


def ascii_clean(value):
    replacements = {
        "\u2013": "-", "\u2014": "-", "\u2011": "-",
        "\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"',
        "\u00a0": " ", "\u2003": " ", "\u200b": "", "\ufeff": "",
    }
    text = str(value or "")
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text.encode("ascii", "ignore").decode("ascii")


def esc(value):
    return html.escape(ascii_clean(value), quote=True)


def paragraph(markup, size=6.0, leading=7.0, color=TEXT, bold=False, align=TA_LEFT):
    style = ParagraphStyle(
        name=f"p{size}{leading}{bold}{align}",
        fontName="Helvetica-Bold" if bold else "Helvetica",
        fontSize=size,
        leading=leading,
        textColor=color,
        alignment=align,
        spaceBefore=0,
        spaceAfter=0,
    )
    return Paragraph(markup, style)


def draw_paragraph(c, markup, x, top_y, width, height, size=6.0, leading=7.0,
                   color=TEXT, bold=False, align=TA_LEFT):
    item = paragraph(markup, size, leading, color, bold, align)
    _, rendered_h = item.wrap(width, height)
    item.drawOn(c, x, top_y - rendered_h - 1)
    return rendered_h


def draw_kpi(c, x, top_y, width, value, label, fill, border):
    value_h = 34
    label_h = 23
    c.setFillColor(fill)
    c.setStrokeColor(fill)
    c.rect(x, top_y - value_h, width, value_h, fill=1, stroke=1)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(x + width / 2, top_y - 23, ascii_clean(value))
    c.setStrokeColor(border)
    c.setLineWidth(0.7)
    c.rect(x, top_y - value_h - label_h - 5, width, label_h, fill=0, stroke=1)
    c.setFillColor(border)
    c.setFont("Helvetica-Bold", 6.5)
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
    draw_paragraph(c, esc(text), MARGIN_X + 51, y + h - 8, CONTENT_W - 62, h - 10,
                   size=6.8, leading=8.3, color=RED, bold=True)


def status_style(status):
    if status == "Done":
        return LIGHT_GREEN, GREEN
    if status == "Ready for Testing":
        return LIGHT_BLUE, BLUE
    if status == "HerdX Accepted":
        return LIGHT_NAVY, NAVY
    if status in {"New / Open", "In Progress"}:
        return LIGHT_AMBER, AMBER
    return LIGHT_RED, RED


def parse_date(value):
    return datetime.strptime(value.strip(), "%d-%b-%y")


def read_records():
    with open(CSV_PATH, "r", encoding="utf-8-sig", newline="") as stream:
        records = [row for row in csv.DictReader(stream) if row.get("Key", "").strip()]
    for record in records:
        for key in record:
            record[key] = ascii_clean(record[key].strip())
        record["_date"] = parse_date(record["Date"])
    return sorted(records, key=lambda r: (r["_date"], r["Key"]), reverse=True)


def draw_header(c, subtitle):
    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(PAGE_W / 2, 807, "WEEKLY STATUS REPORT")
    c.setFillColor(colors.HexColor("#1D2D45"))
    c.setFont("Helvetica-Bold", 8.2)
    c.drawCentredString(PAGE_W / 2, 793, subtitle)


def draw_panels(c, records, status_counts, type_counts):
    top = 620
    height = 125
    gap = 14
    width = (CONTENT_W - 2 * gap) / 3
    panels = [
        (
            "KEY HIGHLIGHTS",
            [
                f"- {status_counts['Done']} of {len(records)} work items are Done.",
                f"- {status_counts['In Progress']} items are currently In Progress.",
                f"- {status_counts['Ready for Testing']} items are Ready for Testing.",
                f"- Work mix: {type_counts['Bug']} bugs, {type_counts['Task']} tasks, {type_counts['Story']} stories.",
            ],
        ),
        (
            "NEXT FOCUS",
            [
                f"- Complete QA validation for {status_counts['Ready for Testing']} Ready for Testing items.",
                f"- Triage the {status_counts['New / Open']} New / Open items.",
                "- Continue the active development work and confirm milestones.",
                "- Follow up on all unassigned work before the next review.",
            ],
        ),
        (
            "MANAGEMENT ATTENTION",
            [
                f"- {status_counts['New / Open']} items require triage or planning.",
                f"- {sum(not r['Assignee'] or r['Assignee'].lower() == 'unassigned' for r in records)} items are unassigned.",
                f"- Track {status_counts['In Progress']} active work items closely.",
                f"- Confirm disposition for {status_counts['HerdX Accepted']} HerdX Accepted item(s).",
            ],
        ),
    ]
    for index, (title, bullets) in enumerate(panels):
        x = MARGIN_X + index * (width + gap)
        y = top - height
        c.setFillColor(colors.white)
        c.setStrokeColor(GRID)
        c.setLineWidth(0.6)
        c.rect(x, y, width, height, fill=1, stroke=1)
        c.setFillColor(colors.HexColor("#F1F3F5"))
        c.rect(x + 8, top - 34, width - 16, 30, fill=1, stroke=0)
        c.setFillColor(NAVY)
        c.setFont("Helvetica-Bold", 9.2)
        c.drawCentredString(x + width / 2, top - 24, title)
        current_y = top - 45
        for bullet in bullets:
            draw_paragraph(c, esc(bullet), x + 10, current_y, width - 20, 30,
                           size=6.8, leading=8.5, color=TEXT)
            current_y -= 23


def table_header(c, top_y, widths, headers):
    x0 = MARGIN_X
    header_h = 19
    c.setFillColor(NAVY)
    c.rect(x0, top_y - header_h, sum(widths), header_h, fill=1, stroke=0)
    x = x0
    for index, header in enumerate(headers):
        draw_paragraph(c, esc(header), x + 2, top_y - 4, widths[index] - 4, header_h - 3,
                       size=5.6, leading=6.2, color=colors.white, bold=True, align=TA_CENTER)
        if index > 0:
            c.setStrokeColor(colors.white)
            c.setLineWidth(0.35)
            c.line(x, top_y - header_h, x, top_y)
        x += widths[index]
    return top_y - header_h


def draw_work_item_rows(c, records, start_index, top_y, bottom_y):
    widths = [18, 239, 56, 85, 96, 47]
    headers = ["#", "KEY / WORK ITEM", "ISSUE TYPE", "STATUS", "OWNER", "DATE"]
    current_y = table_header(c, top_y, widths, headers)
    index = start_index
    while index < len(records):
        record = records[index]
        item_markup = f"<b>{esc(record['Key'])}</b> - {esc(record['Summary'])}"
        date_text = f"{record['_date'].day}-{record['_date'].strftime('%b')}"
        values = [str(index + 1), item_markup, record["Issue Type"], record["Status"], record["Assignee"] or "Unassigned", date_text]
        rendered = []
        max_h = 0
        for col, value in enumerate(values):
            markup = value if col == 1 else esc(value)
            item = paragraph(markup, size=5.55 if col == 1 else 5.2,
                             leading=6.5 if col == 1 else 6.1,
                             color=TEXT, bold=col in {0, 2, 4},
                             align=TA_CENTER if col in {0, 2, 3, 5} else TA_LEFT)
            _, item_h = item.wrap(widths[col] - 6, 100)
            rendered.append(item)
            max_h = max(max_h, item_h)
        row_h = max(24, min(44, max_h + 7))
        if current_y - row_h < bottom_y:
            break

        fill = ROW_ALT if index % 2 else colors.white
        c.setFillColor(fill)
        c.setStrokeColor(GRID)
        c.setLineWidth(0.45)
        c.rect(MARGIN_X, current_y - row_h, sum(widths), row_h, fill=1, stroke=1)
        status_fill, status_text = status_style(record["Status"])
        status_x = MARGIN_X + sum(widths[:3])
        c.setFillColor(status_fill)
        c.rect(status_x, current_y - row_h + 3, widths[3], row_h - 6, fill=1, stroke=0)

        x = MARGIN_X
        for col, item in enumerate(rendered):
            if col == 3:
                item.style.textColor = status_text
                item.style.fontName = "Helvetica-Bold"
            _, item_h = item.wrap(widths[col] - 6, row_h - 4)
            item.drawOn(c, x + 3, current_y - (row_h + item_h) / 2)
            if col > 0:
                c.setStrokeColor(GRID)
                c.setLineWidth(0.35)
                c.line(x, current_y - row_h, x, current_y)
            x += widths[col]
        current_y -= row_h
        index += 1
    return index, current_y


def draw_summary_table(c, records, status_counts, type_counts, top_y):
    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 8.8)
    c.drawString(MARGIN_X + 6, top_y, "STATUS BREAKDOWN")
    widths = [180, 80, 120, 161]
    headers = ["STATUS", "COUNT", "SHARE", "FOLLOW-UP"]
    y = table_header(c, top_y - 13, widths, headers)
    status_order = ["Done", "In Progress", "Ready for Testing", "HerdX Accepted", "New / Open"]
    for number, status in enumerate(status_order):
        count = status_counts[status]
        if not count:
            continue
        fill = ROW_ALT if number % 2 else colors.white
        row_h = 27
        c.setFillColor(fill)
        c.setStrokeColor(GRID)
        c.rect(MARGIN_X, y - row_h, sum(widths), row_h, fill=1, stroke=1)
        status_fill, status_text = status_style(status)
        c.setFillColor(status_fill)
        c.rect(MARGIN_X, y - row_h, widths[0], row_h, fill=1, stroke=0)
        followup = {
            "Done": "No further action in this extract",
            "In Progress": "Continue development",
            "Ready for Testing": "Complete QA validation",
            "HerdX Accepted": "Confirm acceptance and close",
            "New / Open": "Triage and plan",
        }[status]
        values = [status, str(count), f"{count / len(records):.1%}", followup]
        x = MARGIN_X
        for col, value in enumerate(values):
            item = paragraph(esc(value), size=6.6, leading=7.8,
                             color=status_text if col == 0 else TEXT,
                             bold=col == 0, align=TA_CENTER if col in {0, 1, 2} else TA_LEFT)
            _, item_h = item.wrap(widths[col] - 8, row_h - 4)
            item.drawOn(c, x + 4, y - (row_h + item_h) / 2)
            if col > 0:
                c.setStrokeColor(GRID)
                c.setLineWidth(0.35)
                c.line(x, y - row_h, x, y)
            x += widths[col]
        y -= row_h

    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 8.8)
    c.drawString(MARGIN_X + 6, y - 30, "ISSUE TYPE BREAKDOWN")
    type_y = table_header(c, y - 43, [180, 80, 281], ["ISSUE TYPE", "COUNT", "SHARE OF WORK ITEMS"])
    for number, issue_type in enumerate(["Bug", "Task", "Story"]):
        count = type_counts[issue_type]
        row_h = 27
        fill = ROW_ALT if number % 2 else colors.white
        c.setFillColor(fill)
        c.setStrokeColor(GRID)
        c.rect(MARGIN_X, type_y - row_h, 541, row_h, fill=1, stroke=1)
        values = [issue_type, str(count), f"{count / len(records):.1%}"]
        x = MARGIN_X
        for col, value in enumerate(values):
            item = paragraph(esc(value), size=6.6, leading=7.8, color=TEXT,
                             bold=col == 0, align=TA_CENTER if col < 2 else TA_LEFT)
            _, item_h = item.wrap([180, 80, 281][col] - 8, row_h - 4)
            item.drawOn(c, x + 4, type_y - (row_h + item_h) / 2)
            if col > 0:
                c.setStrokeColor(GRID)
                c.setLineWidth(0.35)
                c.line(x, type_y - row_h, x, type_y)
            x += [180, 80, 281][col]
        type_y -= row_h


def draw_footer(c, page_number):
    c.setFillColor(MUTED)
    c.setFont("Helvetica", 5.8)
    c.drawString(MARGIN_X, 22, "Sprint 102 | Source: sprint102_workitems.csv")
    c.setFillColor(NAVY)
    c.setFont("Helvetica", 7.2)
    c.drawRightString(PAGE_W - MARGIN_X, 22, f"Page {page_number}")


def main():
    records = read_records()
    status_counts = Counter(record["Status"] for record in records)
    type_counts = Counter(record["Issue Type"] for record in records)
    total = len(records)
    completed = status_counts["Done"]
    active = total - completed
    start_date = min(record["_date"] for record in records)
    end_date = max(record["_date"] for record in records)
    subtitle = f"Sprint 102 | Week of {start_date.day}-{end_date.day} {end_date.strftime('%b %Y')}"

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    c = canvas.Canvas(OUTPUT_PATH, pagesize=A4)
    c.setTitle("Sprint 102 Weekly Status Report")
    c.setAuthor("Jira Weekly Status Report")

    # First page: match the attached WSR overview structure.
    draw_header(c, subtitle)
    card_gap = 9
    card_w = (CONTENT_W - 3 * card_gap) / 4
    cards = [
        (str(total), "WORK ITEMS", NAVY, NAVY),
        (str(status_counts["In Progress"]), "IN PROGRESS", GREEN, GREEN),
        (str(completed), "COMPLETED", BLUE, BLUE),
        (str(active), "OPEN / PENDING", RED, RED),
    ]
    for index, (value, label, fill, border) in enumerate(cards):
        draw_kpi(c, MARGIN_X + index * (card_w + card_gap), 763, card_w, value, label, fill, border)

    draw_banner(c, 650, f"OVERALL STATUS: AT RISK {active} of {total} work items are not Done and require follow-up.")
    draw_panels(c, records, status_counts, type_counts)
    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 8.8)
    c.drawString(MARGIN_X + 6, 477, f"SPRINT 102 - WORK ITEM SNAPSHOT (ALL {total} ITEMS)")
    next_index, current_y = draw_work_item_rows(c, records, 0, 464, 48)
    draw_footer(c, 1)

    # Continuation pages keep the attached report's table-first pagination.
    page_number = 1
    while next_index < total:
        c.showPage()
        page_number += 1
        next_index, current_y = draw_work_item_rows(c, records, next_index, 800, 48)
        draw_footer(c, page_number)

    # Use the remaining space after the final rows when possible, avoiding a sparse page.
    if current_y > 430:
        draw_summary_table(c, records, status_counts, type_counts, current_y - 28)
    else:
        c.showPage()
        page_number += 1
        draw_header(c, subtitle)
        draw_summary_table(c, records, status_counts, type_counts, 730)

    total_pages = page_number
    draw_footer(c, total_pages)
    c.save()
    print({"output": OUTPUT_PATH, "records": total, "completed": completed, "active": active, "pages": total_pages})


if __name__ == "__main__":
    main()
