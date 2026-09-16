import csv
import html
import os
import re
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph


CSV_PATH = r"C:\Users\PinkyAhmed\Downloads\production_and_firebase_bugs.csv"
OUTPUT_PATH = r"C:\work\jira-weekly-status-report\output\pdf\Sprint_101_Production_Bugs.pdf"

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
LINK = colors.HexColor("#2468C5")


def ascii_clean(value):
    replacements = {
        "\u2013": "-", "\u2014": "-", "\u2011": "-",
        "\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"',
        "\ufffd": "-", "\u00a0": " ", "\u2003": " ",
        "\u200b": "", "\ufeff": "",
    }
    text = str(value or "")
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text.encode("ascii", "ignore").decode("ascii")


def esc(value):
    return html.escape(ascii_clean(value), quote=True)


def para(text, size=5.3, leading=6.2, color=TEXT, bold=False, align=TA_LEFT):
    style = ParagraphStyle(
        name=f"p{size}{leading}{bold}{align}",
        fontName="Helvetica-Bold" if bold else "Helvetica",
        fontSize=size,
        leading=leading,
        textColor=color,
        alignment=align,
        spaceAfter=0,
        spaceBefore=0,
    )
    return Paragraph(text, style)


def draw_paragraph(c, text, x, top_y, width, height, size=5.3, leading=6.2,
                   color=TEXT, bold=False, align=TA_LEFT):
    item = para(text, size, leading, color, bold, align)
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
    c.setFont("Helvetica-Bold", 6.4)
    c.drawCentredString(x + width / 2, top_y - value_h - 19, ascii_clean(label).upper())


def draw_banner(c, y, text):
    h = 42
    c.setFillColor(RED)
    c.rect(MARGIN_X, y, CONTENT_W, h, fill=1, stroke=0)
    c.setFillColor(LIGHT_RED)
    c.rect(MARGIN_X + 44, y, CONTENT_W - 44, h, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 20)
    c.drawCentredString(MARGIN_X + 22, y + 13, "!")
    draw_paragraph(c, esc(text), MARGIN_X + 51, y + h - 8, CONTENT_W - 62, h - 10,
                   size=6.7, leading=8.2, color=RED, bold=True)


def status_style(status):
    if status == "Done":
        return LIGHT_GREEN, GREEN
    if status == "Ready for Testing":
        return LIGHT_BLUE, BLUE
    if status == "HerdX Accepted":
        return LIGHT_NAVY, NAVY
    if status in {"New / Open", "Duplicate", "In Progress"}:
        return LIGHT_AMBER, AMBER
    return LIGHT_RED, RED


def status_display(status):
    return ascii_clean(status).replace(" / ", "/")


def sort_key(record):
    try:
        date = datetime.strptime(record["Date"], "%m/%d/%Y")
    except ValueError:
        date = datetime.min
    match = re.search(r"(\d+)$", record["Key"])
    ticket_number = int(match.group(1)) if match else 0
    return date, ticket_number


def read_records():
    with open(CSV_PATH, "r", encoding="utf-8-sig", newline="") as stream:
        records = [row for row in csv.DictReader(stream) if row.get("Key", "").strip()]
    for record in records:
        for key in record:
            record[key] = ascii_clean(record[key].strip())
    return sorted(records, key=sort_key, reverse=True)


def draw_header(c, subtitle):
    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 15.5)
    c.drawCentredString(PAGE_W / 2, 808, "PRODUCTION + FIREBASE BUG REPORT")
    c.setFont("Helvetica-Bold", 8.1)
    c.setFillColor(colors.HexColor("#1D2D45"))
    c.drawCentredString(PAGE_W / 2, 793, subtitle)


def draw_section_title(c, y, title):
    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 8.8)
    c.drawString(MARGIN_X + 6, y, title)


def cell_markup(record, field, row_height):
    value = esc(record[field]) if record[field] else "-"
    if field == "Key":
        return f'<font color="#2468C5"><u><b>{value}</b></u></font><br/><font size="4.1" color="#4A6B96">Open Jira</font>'
    if field == "Status":
        return value
    return value


def draw_data_table(c, records, top_y):
    # The last column carries the complete summary and source URL while the key is
    # an active Jira link. Category is still shown explicitly for CSV fidelity.
    widths = [18, 68, 34, 66, 70, 74, 48, 163]
    headers = ["#", "KEY", "TYPE", "CATEGORY", "STATUS", "OWNER", "DATE", "SUMMARY / SOURCE URL"]
    x0 = MARGIN_X
    header_h = 22
    c.setFillColor(NAVY)
    c.rect(x0, top_y - header_h, sum(widths), header_h, fill=1, stroke=0)
    x = x0
    for index, header in enumerate(headers):
        draw_paragraph(c, esc(header), x + 2, top_y - 5, widths[index] - 4, header_h - 4,
                       size=5.0, leading=5.6, color=colors.white, bold=True, align=TA_CENTER)
        if index > 0:
            c.setStrokeColor(colors.white)
            c.setLineWidth(0.35)
            c.line(x, top_y - header_h, x, top_y)
        x += widths[index]

    current_y = top_y - header_h
    row_bounds = []
    for number, record in enumerate(records, start=1):
        summary = esc(record["Summary"])
        source_url = esc(record["URL"])
        summary_markup = (
            f"{summary}<br/>"
            f'<font size="4.0" color="#4A6B96">URL: {source_url}</font>'
        )
        values = [
            str(number), record["Key"], record["Issue Type"], record["Category"],
            record["Status"], record["Assignee"] or "-", record["Date"], summary_markup,
        ]
        rendered = []
        max_h = 0
        for index, value in enumerate(values):
            if index == 1:
                markup = cell_markup(record, "Key", 0)
            elif index == 7:
                markup = value
            else:
                markup = esc(value)
            item = para(markup, size=4.8 if index not in {0, 1} else 5.0,
                        leading=5.7 if index not in {0, 1} else 5.9,
                        color=TEXT, bold=index in {1, 5},
                        align=TA_CENTER if index in {0, 1, 2, 3, 4, 6} else TA_LEFT)
            _, item_h = item.wrap(widths[index] - 6, 200)
            rendered.append(item)
            max_h = max(max_h, item_h)
        row_h = max(38, min(68, max_h + 8))
        fill = ROW_ALT if number % 2 == 0 else colors.white
        c.setFillColor(fill)
        c.setStrokeColor(GRID)
        c.setLineWidth(0.45)
        c.rect(x0, current_y - row_h, sum(widths), row_h, fill=1, stroke=1)

        status_fill, status_text = status_style(record["Status"])
        status_x = x0 + sum(widths[:4])
        c.setFillColor(status_fill)
        c.rect(status_x, current_y - row_h + 3, widths[4], row_h - 6, fill=1, stroke=0)

        x = x0
        for index, item in enumerate(rendered):
            if index == 4:
                item.style.textColor = status_text
                item.style.fontName = "Helvetica-Bold"
            _, item_h = item.wrap(widths[index] - 6, row_h - 4)
            item.drawOn(c, x + 3, current_y - (row_h + item_h) / 2)
            if index > 0:
                c.setStrokeColor(GRID)
                c.setLineWidth(0.35)
                c.line(x, current_y - row_h, x, current_y)
            if index == 1:
                c.linkURL(record["URL"], (x + 2, current_y - row_h + 2, x + widths[index] - 2, current_y - 2), relative=0)
            x += widths[index]
        row_bounds.append((current_y, row_h))
        current_y -= row_h
    return current_y


def draw_footer(c, page_number, total_pages):
    c.setFillColor(NAVY)
    c.setFont("Helvetica", 7.2)
    c.drawRightString(PAGE_W - MARGIN_X, 22, f"Page {page_number} of {total_pages}")
    c.setFillColor(colors.HexColor("#5E718E"))
    c.setFont("Helvetica", 5.8)
    c.drawString(MARGIN_X, 22, "Imported from production_and_firebase_bugs.csv | Ticket keys link to Jira")


def main():
    records = read_records()
    production = [r for r in records if r["Category"] == "Production Bug"]
    firebase = [r for r in records if r["Category"] == "Firebase Crash"]
    completed = sum(r["Status"] == "Done" for r in records)
    open_pending = len(records) - completed
    dates = [datetime.strptime(r["Date"], "%m/%d/%Y") for r in records]
    date_start = min(dates).strftime("%-d") if os.name != "nt" else min(dates).strftime("%d").lstrip("0")
    date_end = max(dates).strftime("%-d") if os.name != "nt" else max(dates).strftime("%d").lstrip("0")
    date_end_text = max(dates).strftime("%b %Y")
    subtitle = f"Sprint 101 | Week of {date_start}-{date_end} {date_end_text} | Source: production and firebase bugs"

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    c = canvas.Canvas(OUTPUT_PATH, pagesize=A4)
    c.setTitle("Sprint 101 Production and Firebase Bug Report")
    c.setAuthor("Jira Weekly Status Report")

    draw_header(c, subtitle)
    card_gap = 9
    card_w = (CONTENT_W - 3 * card_gap) / 4
    cards = [
        (str(len(records)), "TOTAL TICKETS", NAVY, NAVY),
        (str(len(production)), "PRODUCTION BUGS", GREEN, GREEN),
        (str(len(firebase)), "FIREBASE CRASHES", BLUE, BLUE),
        (str(completed), "COMPLETED", RED, RED),
    ]
    for index, (value, label, fill, border) in enumerate(cards):
        draw_kpi(c, MARGIN_X + index * (card_w + card_gap), 763, card_w, value, label, fill, border)

    draw_banner(c, 650, f"REPORT STATUS: {open_pending} of {len(records)} tickets remain open or pending review.")
    c.setFillColor(colors.HexColor("#5E718E"))
    c.setFont("Helvetica", 6.2)
    c.drawString(MARGIN_X + 6, 637, f"Dataset coverage: {len(production)} Production Bug records and {len(firebase)} Firebase Crash records")

    draw_section_title(c, 620, f"PRODUCTION BUGS - CURRENT STATUS ({len(production)})")
    draw_data_table(c, production, 608)
    draw_footer(c, 1, 2)
    c.showPage()

    draw_header(c, subtitle)
    draw_section_title(c, 757, f"FIREBASE CRASHES - CURRENT STATUS ({len(firebase)})")
    draw_data_table(c, firebase, 745)
    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 8.5)
    c.drawString(MARGIN_X + 6, 525, "STATUS BREAKDOWN")
    breakdown = {}
    for record in records:
        breakdown[record["Status"]] = breakdown.get(record["Status"], 0) + 1
    y = 507
    for status in sorted(breakdown):
        fill, text_color = status_style(status)
        c.setFillColor(fill)
        c.roundRect(MARGIN_X + 6, y - 15, 178, 18, 3, fill=1, stroke=0)
        c.setFillColor(text_color)
        c.setFont("Helvetica-Bold", 6.3)
        c.drawString(MARGIN_X + 14, y - 9, status_display(status))
        c.setFillColor(TEXT)
        c.setFont("Helvetica", 6.3)
        c.drawRightString(MARGIN_X + 174, y - 9, f"{breakdown[status]} ticket(s)")
        y -= 24

    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 8.5)
    c.drawString(MARGIN_X + 6, 372, "REPORT NOTES")
    notes = [
        "All fields from the supplied CSV are represented: Key, Summary, Issue Type, Category, Status, Assignee, Date, and URL.",
        "Each ticket key is an active link to its source Jira URL; the full URL is also printed beneath the summary.",
        "Records are grouped by the CSV Category field and ordered by date, then ticket number, newest first.",
    ]
    y = 354
    for note in notes:
        c.setFillColor(NAVY)
        c.circle(MARGIN_X + 9, y + 2, 2, fill=1, stroke=0)
        draw_paragraph(c, esc(note), MARGIN_X + 18, y + 7, CONTENT_W - 25, 28,
                       size=6.6, leading=8.2, color=TEXT)
        y -= 30

    draw_footer(c, 2, 2)
    c.showPage()
    c.save()
    print({
        "output": OUTPUT_PATH,
        "records": len(records),
        "production": len(production),
        "firebase": len(firebase),
        "completed": completed,
        "open_pending": open_pending,
        "pages": 2,
    })


if __name__ == "__main__":
    main()
