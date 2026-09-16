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

NAVY = colors.HexColor("#1F4785")
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


def paragraph(markup, size=5.5, leading=6.5, color=TEXT, bold=False, align=TA_LEFT):
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


def draw_paragraph(c, markup, x, top_y, width, height, size=5.5, leading=6.5,
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
    draw_paragraph(c, esc(text), MARGIN_X + 51, y + h - 8, CONTENT_W - 62, h - 10,
                   size=6.8, leading=8.3, color=RED, bold=True)


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


def sort_key(record):
    try:
        date = datetime.strptime(record["Date"], "%m/%d/%Y")
    except ValueError:
        date = datetime.min
    match = re.search(r"(\d+)$", record["Key"])
    return date, int(match.group(1)) if match else 0


def read_records():
    with open(CSV_PATH, "r", encoding="utf-8-sig", newline="") as stream:
        records = [row for row in csv.DictReader(stream) if row.get("Key", "").strip()]
    for record in records:
        for key in record:
            record[key] = ascii_clean(record[key].strip())
    return sorted(records, key=sort_key, reverse=True)


def draw_ticket_table(c, records, top_y):
    widths = [18, 83, 51, 71, 82, 237]
    headers = ["#", "TICKET", "TYPE", "STATUS", "OWNER", "SUMMARY / NOTES"]
    x0 = MARGIN_X
    header_h = 18
    total_w = sum(widths)
    c.setFillColor(NAVY)
    c.rect(x0, top_y - header_h, total_w, header_h, fill=1, stroke=0)
    x = x0
    for index, header in enumerate(headers):
        draw_paragraph(c, esc(header), x + 2, top_y - 4, widths[index] - 4, header_h - 3,
                       size=5.7, leading=6.3, color=colors.white, bold=True, align=TA_CENTER)
        if index > 0:
            c.setStrokeColor(colors.white)
            c.setLineWidth(0.35)
            c.line(x, top_y - header_h, x, top_y)
        x += widths[index]

    current_y = top_y - header_h
    for number, record in enumerate(records, start=1):
        meta = f"{record['Category']} | {record['Date']}"
        summary_markup = f"{esc(record['Summary'])}<br/><font size=4.1 color=\"#4A6B96\">{esc(meta)}</font>"
        values = [number, record["Key"], record["Issue Type"], record["Status"], record["Assignee"] or "-", summary_markup]
        rendered = []
        max_h = 0
        for index, value in enumerate(values):
            if index == 1:
                markup = f'<font color="#2468C5"><u><b>{esc(value)}</b></u></font>'
            elif index == 5:
                markup = value
            else:
                markup = esc(value)
            item = paragraph(markup, size=5.05 if index != 5 else 4.85,
                             leading=5.8 if index != 5 else 5.7,
                             color=TEXT, bold=index in {1, 4},
                             align=TA_CENTER if index in {0, 1, 2, 3} else TA_LEFT)
            _, item_h = item.wrap(widths[index] - 6, 100)
            rendered.append(item)
            max_h = max(max_h, item_h)
        row_h = max(25, min(35, max_h + 7))
        fill = ROW_ALT if number % 2 == 0 else colors.white
        c.setFillColor(fill)
        c.setStrokeColor(GRID)
        c.setLineWidth(0.45)
        c.rect(x0, current_y - row_h, total_w, row_h, fill=1, stroke=1)

        status_fill, status_text = status_style(record["Status"])
        status_x = x0 + sum(widths[:3])
        c.setFillColor(status_fill)
        c.rect(status_x, current_y - row_h + 3, widths[3], row_h - 6, fill=1, stroke=0)

        x = x0
        for index, item in enumerate(rendered):
            if index == 3:
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
        current_y -= row_h
    return current_y


def main():
    records = read_records()
    completed = sum(record["Status"] == "Done" for record in records)
    in_progress = sum(record["Status"] == "In Progress" for record in records)
    open_pending = len(records) - completed
    dates = [datetime.strptime(record["Date"], "%m/%d/%Y") for record in records]
    start_date, end_date = min(dates), max(dates)
    subtitle = f"Sprint 102 | Week of {start_date.day}-{end_date.day} {end_date.strftime('%b %Y')}"

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    c = canvas.Canvas(OUTPUT_PATH, pagesize=A4)
    c.setTitle("Sprint 102 Production Ticket Report")
    c.setAuthor("Jira Weekly Status Report")

    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(PAGE_W / 2, 807, "PRODUCTION TICKET REPORT")
    c.setFont("Helvetica-Bold", 8.2)
    c.setFillColor(colors.HexColor("#1D2D45"))
    c.drawCentredString(PAGE_W / 2, 793, subtitle)

    card_gap = 9
    card_w = (CONTENT_W - 3 * card_gap) / 4
    cards = [
        (str(len(records)), "PRODUCTION TICKETS", NAVY, NAVY),
        (str(in_progress), "IN PROGRESS", GREEN, GREEN),
        (str(completed), "COMPLETED", BLUE, BLUE),
        (str(open_pending), "OPEN / PENDING", RED, RED),
    ]
    for index, (value, label, fill, border) in enumerate(cards):
        draw_kpi(c, MARGIN_X + index * (card_w + card_gap), 763, card_w, value, label, fill, border)

    draw_banner(c, 650, f"PRODUCTION STATUS: AT RISK {open_pending} tickets remain open or pending review.")
    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 8.8)
    c.drawString(MARGIN_X + 6, 620, "PRODUCTION TICKETS - CURRENT STATUS")
    draw_ticket_table(c, records, 607)

    c.setFillColor(NAVY)
    c.setFont("Helvetica", 7.2)
    c.drawRightString(PAGE_W - MARGIN_X, 22, "Page 1")
    c.save()
    print({"output": OUTPUT_PATH, "records": len(records), "completed": completed, "open_pending": open_pending, "pages": 1})


if __name__ == "__main__":
    main()
