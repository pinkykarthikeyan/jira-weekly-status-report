import csv
import os
import re

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph


CSV_PATH = r"C:\Users\PinkyAhmed\Downloads\Jira (3).csv"
OUTPUT_PATH = r"C:\work\jira-weekly-status-report\output\pdf\sprint_production_bugs.pdf"

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
    header_map = {}
    for index, value in enumerate(header):
        header_map.setdefault(value, []).append(index)
    summary_index = header_map["Summary"][0]
    key_index = header_map["Issue key"][0]
    type_index = header_map["Issue Type"][0]
    status_index = header_map["Status"][0]
    assignee_index = header_map["Assignee"][0]
    label_indexes = header_map.get("Labels", [])
    production_index = header_map.get("Production Bug", [None])[0]
    records = []
    for raw in rows:
        if not raw or not raw[key_index].strip():
            continue
        records.append({
            "Key": raw[key_index].strip(),
            "Summary": raw[summary_index].strip(),
            "Issue Type": raw[type_index].strip(),
            "Assignee": raw[assignee_index].strip(),
            "Status": raw[status_index].strip(),
            "Labels": ",".join(raw[index].strip() for index in label_indexes if index < len(raw) and raw[index].strip()),
            "Production Bug": raw[production_index].strip() if production_index is not None and production_index < len(raw) else "Yes",
        })
    return records


def paragraph(text, size=5.5, leading=6.5, color=TEXT, bold=False, align=TA_LEFT):
    style = ParagraphStyle(
        name=f"p{size}{leading}{bold}{align}", fontName="Helvetica-Bold" if bold else "Helvetica",
        fontSize=size, leading=leading, textColor=color, alignment=align,
    )
    safe = ascii_clean(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return Paragraph(safe, style)


def draw_paragraph(c, text, x, top_y, width, height, size=5.5, leading=6.5, color=TEXT, bold=False, align=TA_LEFT):
    para = paragraph(text, size, leading, color, bold, align)
    _, rendered_h = para.wrap(width, height)
    para.drawOn(c, x, top_y - rendered_h - 1)


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


def status_style(status):
    if status == "Done":
        return LIGHT_GREEN, GREEN
    if status == "In Progress":
        return LIGHT_AMBER, colors.HexColor("#C47F00")
    if status == "Ready for Testing":
        return LIGHT_BLUE, BLUE
    if status == "HerdX Accepted":
        return LIGHT_NAVY, NAVY
    if status in {"Cannot Reproduce", "Rejected / Not a Bug", "Discarded"}:
        return LIGHT_RED, NAVY
    return LIGHT_BLUE, BLUE


def draw_ticket_table(c, tickets, top_y):
    col_widths = [18, 83, 51, 71, 82, 237]
    x0 = MARGIN_X
    header_h = 18
    row_h = 22
    total_w = sum(col_widths)
    c.setFillColor(NAVY)
    c.rect(x0, top_y - header_h, total_w, header_h, fill=1, stroke=0)
    headers = ["#", "TICKET", "TYPE", "STATUS", "OWNER", "SUMMARY / NOTES"]
    x = x0
    for idx, header in enumerate(headers):
        draw_paragraph(c, header, x + 2, top_y - 4, col_widths[idx] - 4, header_h - 3, size=5.7, leading=6.3, color=colors.white, bold=True, align=1)
        if idx > 0:
            c.setStrokeColor(colors.white)
            c.setLineWidth(0.35)
            c.line(x, top_y - header_h, x, top_y)
        x += col_widths[idx]
    current_y = top_y - header_h
    for number, ticket in enumerate(tickets, start=1):
        fill = ROW_ALT if number % 2 == 0 else colors.white
        c.setFillColor(fill)
        c.setStrokeColor(GRID)
        c.setLineWidth(0.45)
        c.rect(x0, current_y - row_h, total_w, row_h, fill=1, stroke=1)
        status_fill, status_text = status_style(ticket["Status"])
        status_x = x0 + col_widths[0] + col_widths[1] + col_widths[2]
        c.setFillColor(status_fill)
        c.rect(status_x, current_y - row_h + 3, col_widths[3], row_h - 6, fill=1, stroke=0)
        values = [
            str(number), ticket["Key"], ticket["Issue Type"], ticket["Status"], ticket["Assignee"] or "-", ticket["Summary"],
        ]
        x = x0
        for idx, value in enumerate(values):
            text_color = status_text if idx == 3 else TEXT
            draw_paragraph(c, value, x + 2, current_y - 3, col_widths[idx] - 4, row_h - 3, size=5.15 if idx != 0 else 5.2, leading=6.0, color=text_color, bold=(idx in {1, 4}), align=1 if idx in {0, 1, 2, 3} else TA_LEFT)
            if idx > 0:
                c.setStrokeColor(GRID)
                c.setLineWidth(0.35)
                c.line(x, current_y - row_h, x, current_y)
            x += col_widths[idx]
        current_y -= row_h
    return current_y


def footer(c, page_number):
    c.setFillColor(NAVY)
    c.setFont("Helvetica", 7.2)
    c.drawRightString(PAGE_W - MARGIN_X, 22, f"Page {page_number}")


def main():
    records = parse_records(CSV_PATH)
    tickets = [r for r in records if r["Production Bug"] == "Yes"]
    tickets.sort(key=lambda r: int(re.search(r"(\d+)$", r["Key"]).group(1)), reverse=True)
    completed = sum(r["Status"] == "Done" for r in tickets)
    in_progress = sum(r["Status"] == "In Progress" for r in tickets)
    open_pending = sum(r["Status"] != "Done" for r in tickets)

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    c = canvas.Canvas(OUTPUT_PATH, pagesize=A4)
    c.setTitle("Sprint 101 Production Ticket Report")

    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(PAGE_W / 2, 807, "PRODUCTION TICKET REPORT")
    c.setFont("Helvetica-Bold", 8.2)
    c.setFillColor(colors.HexColor("#1D2D45"))
    c.drawCentredString(PAGE_W / 2, 793, "Sprint 101 | Week of 31 Aug-4 Sep 2026 | Labels: prod or firebase")

    card_gap = 9
    card_w = (CONTENT_W - 3 * card_gap) / 4
    card_y = 763
    cards = [
        (str(len(tickets)), "PRODUCTION TICKETS", NAVY, NAVY),
        (str(in_progress), "IN PROGRESS", GREEN, GREEN),
        (str(completed), "COMPLETED", BLUE, BLUE),
        (str(open_pending), "OPEN / PENDING", RED, RED),
    ]
    for idx, (value, label, fill, border) in enumerate(cards):
        draw_kpi(c, MARGIN_X + idx * (card_w + card_gap), card_y, card_w, value, label, fill, border)

    draw_banner(c, 650, f"PRODUCTION STATUS: AT RISK  {open_pending} production tickets remain open or pending review.")

    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 8.8)
    c.drawString(MARGIN_X + 6, 620, "PRODUCTION TICKETS - CURRENT STATUS")
    draw_ticket_table(c, tickets, 607)
    footer(c, 1)
    c.showPage()
    c.save()
    print({"output": OUTPUT_PATH, "production_tickets": len(tickets), "completed": completed, "open_pending": open_pending, "pages": 1})


if __name__ == "__main__":
    main()
