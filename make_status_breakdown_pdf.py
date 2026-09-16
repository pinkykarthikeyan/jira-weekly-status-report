import csv
import os
from collections import Counter
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas


CSV_PATH = r"C:\Users\PinkyAhmed\Downloads\production_and_firebase_bugs.csv"
OUTPUT_PATH = r"C:\work\jira-weekly-status-report\output\pdf\Sprint_101_Production_Bugs_Status_Breakdown.pdf"

PAGE_W, PAGE_H = A4
MARGIN_X = 27
CONTENT_W = PAGE_W - 2 * MARGIN_X

NAVY = colors.HexColor("#244C86")
GREEN = colors.HexColor("#0A993F")
BLUE = colors.HexColor("#2468C5")
RED = colors.HexColor("#ED1C24")
AMBER = colors.HexColor("#C47F00")
LIGHT_GREEN = colors.HexColor("#E8F6EC")
LIGHT_BLUE = colors.HexColor("#EAF3FD")
LIGHT_NAVY = colors.HexColor("#DCE7F4")
LIGHT_AMBER = colors.HexColor("#FFF1D2")
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


def read_records():
    with open(CSV_PATH, "r", encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def status_style(status):
    if status == "Done":
        return LIGHT_GREEN, GREEN
    if status == "Ready for Testing":
        return LIGHT_BLUE, BLUE
    if status == "HerdX Accepted":
        return LIGHT_NAVY, NAVY
    return LIGHT_AMBER, AMBER


def main():
    records = read_records()
    counts = Counter(row["Status"].strip() for row in records if row.get("Status"))
    dates = [datetime.strptime(row["Date"], "%m/%d/%Y") for row in records if row.get("Date")]
    start_date, end_date = min(dates), max(dates)
    subtitle = (
        f"Sprint 101 | Week of {start_date.day}-{end_date.day} {end_date.strftime('%b %Y')} | "
        "Labels: prod or firebase"
    )

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    c = canvas.Canvas(OUTPUT_PATH, pagesize=A4)
    c.setTitle("Sprint 101 Status Breakdown")
    c.setAuthor("Jira Weekly Status Report")

    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(PAGE_W / 2, 807, "PRODUCTION TICKET REPORT")
    c.setFillColor(colors.HexColor("#1D2D45"))
    c.setFont("Helvetica-Bold", 8.2)
    c.drawCentredString(PAGE_W / 2, 793, ascii_clean(subtitle))

    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 8.8)
    c.drawString(MARGIN_X + 6, 716, "STATUS BREAKDOWN")
    c.setStrokeColor(colors.HexColor("#B8C7D9"))
    c.setLineWidth(0.6)
    c.line(MARGIN_X + 6, 706, PAGE_W - MARGIN_X - 6, 706)

    preferred_order = ["Done", "Ready for Testing", "HerdX Accepted", "New / Open", "Duplicate"]
    statuses = [status for status in preferred_order if status in counts]
    statuses.extend(status for status in sorted(counts) if status not in statuses)
    row_x = MARGIN_X + 6
    row_w = CONTENT_W - 12
    row_h = 30
    gap = 11
    y = 674
    for status in statuses:
        fill, text_color = status_style(status)
        c.setFillColor(fill)
        c.roundRect(row_x, y - row_h, row_w, row_h, 4, fill=1, stroke=0)
        c.setFillColor(text_color)
        c.setFont("Helvetica-Bold", 8.2)
        c.drawString(row_x + 15, y - 19, ascii_clean(status))
        c.setFillColor(TEXT)
        c.setFont("Helvetica", 8.2)
        label = "ticket" if counts[status] == 1 else "tickets"
        c.drawRightString(row_x + row_w - 15, y - 19, f"{counts[status]} {label}")
        y -= row_h + gap

    c.setFillColor(colors.HexColor("#5E718E"))
    c.setFont("Helvetica", 6.5)
    c.drawString(row_x, y - 2, f"Total tickets represented: {sum(counts.values())}")
    c.setFillColor(NAVY)
    c.setFont("Helvetica", 7.2)
    c.drawRightString(PAGE_W - MARGIN_X, 22, "Page 1")
    c.save()
    print({"output": OUTPUT_PATH, "total_tickets": sum(counts.values()), "status_counts": dict(counts)})


if __name__ == "__main__":
    main()
