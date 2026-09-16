import os
from collections import Counter, defaultdict

from docx import Document
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

from report_generator import col, filter_rows, kind, norm, owner, read_jira_csv

NAVY = "1F2937"
TEXT = "1F2937"
MUTED = "6B7280"
GRID = "D1D5DB"
ROW_ALT = "F7F9FB"
LIGHT_BLUE = "EAF3FD"
LIGHT_GREEN = "E8F6EC"
LIGHT_AMBER = "FFF1D2"
LIGHT_RED = "FFF0F0"
GREEN = "059669"
BLUE = "2563EB"
AMBER = "D97706"
RED = "DC2626"
CONTENT_WIDTH_IN = 7.25


def _shade(cell, color):
    properties = cell._tc.get_or_add_tcPr()
    shading = properties.find(qn("w:shd"))
    if shading is None:
        shading = OxmlElement("w:shd")
        properties.append(shading)
    shading.set(qn("w:fill"), color)


def _borders(table, color=GRID, size="6"):
    properties = table._tbl.tblPr
    borders = properties.first_child_found_in("w:tblBorders")
    if borders is None:
        borders = OxmlElement("w:tblBorders")
        properties.append(borders)
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        tag = "w:" + edge
        element = borders.find(qn(tag))
        if element is None:
            element = OxmlElement(tag)
            borders.append(element)
        element.set(qn("w:val"), "single")
        element.set(qn("w:sz"), size)
        element.set(qn("w:color"), color)


def _set_table_width(table, width_in=CONTENT_WIDTH_IN):
    properties = table._tbl.tblPr
    table_width = properties.find(qn("w:tblW"))
    if table_width is None:
        table_width = OxmlElement("w:tblW")
        properties.append(table_width)
    table_width.set(qn("w:w"), str(int(width_in * 1440)))
    table_width.set(qn("w:type"), "dxa")
    table_layout = properties.find(qn("w:tblLayout"))
    if table_layout is None:
        table_layout = OxmlElement("w:tblLayout")
        properties.append(table_layout)
    table_layout.set(qn("w:type"), "fixed")


def _set_cell(cell, text, *, bold=False, color=TEXT, size=8, align=WD_ALIGN_PARAGRAPH.LEFT, fill=None, margin=60, runs=None):
    cell.text = ""
    paragraph = cell.paragraphs[0]
    paragraph.alignment = align
    paragraph.paragraph_format.space_after = Pt(0)
    for run_text, run_bold, run_color in (runs or [(str(text or ""), bold, color)]):
        run = paragraph.add_run(run_text)
        run.bold = run_bold
        run.font.name = "Arial"
        run.font.size = Pt(size)
        run.font.color.rgb = RGBColor.from_string(run_color)
    cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
    properties = cell._tc.get_or_add_tcPr()
    cell_margins = properties.find(qn("w:tcMar"))
    if cell_margins is None:
        cell_margins = OxmlElement("w:tcMar")
        properties.append(cell_margins)
    for side in ("top", "bottom"):
        element = cell_margins.find(qn("w:" + side))
        if element is None:
            element = OxmlElement("w:" + side)
            cell_margins.append(element)
        element.set(qn("w:w"), str(margin))
        element.set(qn("w:type"), "dxa")
    if fill:
        _shade(cell, fill)


def _table(document, rows, widths, header=True, status_column=None, body_size=7.4, cell_margin=60, fills=None):
    table = document.add_table(rows=len(rows), cols=len(rows[0]))
    table.alignment = WD_TABLE_ALIGNMENT.LEFT
    table.autofit = False
    _borders(table)
    _set_table_width(table)
    for row_index, row in enumerate(rows):
        for column_index, value in enumerate(row):
            cell = table.cell(row_index, column_index)
            cell.width = Inches(widths[column_index])
            fill = NAVY if header and row_index == 0 else (fills[column_index] if fills and row_index == 0 else (ROW_ALT if row_index % 2 == (0 if header else 1) else "FFFFFF"))
            text_color = "FFFFFF" if header and row_index == 0 else TEXT
            cell_bold = header and row_index == 0
            cell_color = text_color
            if not cell_bold and column_index == 0:
                cell_color = MUTED
            if not cell_bold and column_index == 2 and str(value) == "Unassigned":
                cell_bold, cell_color = True, RED
            if not cell_bold and column_index == len(row) - 1:
                progress = str(value)
                if progress == "No linked tasks":
                    cell_bold, cell_color = True, MUTED
                elif "100%" in progress:
                    cell_bold, cell_color = True, GREEN
                elif "/" in progress:
                    cell_bold, cell_color = True, AMBER
            _set_cell(cell, value, bold=cell_bold, color=cell_color, size=7.5 if header else body_size, align=WD_ALIGN_PARAGRAPH.CENTER if header else WD_ALIGN_PARAGRAPH.LEFT, fill=fill, margin=cell_margin)
            if status_column is not None and row_index > 0 and column_index == status_column:
                status = str(value)
                status_fill, status_color = {
                    "Done": (LIGHT_GREEN, GREEN),
                    "Ready for Testing": (LIGHT_BLUE, BLUE),
                    "HerdX Accepted": ("DCE7F4", NAVY),
                    "New / Open": (LIGHT_AMBER, AMBER),
                    "In Progress": (LIGHT_AMBER, AMBER),
                }.get(status, (LIGHT_RED, RED))
                _set_cell(cell, status, bold=True, color=status_color, size=body_size, align=WD_ALIGN_PARAGRAPH.CENTER, fill=status_fill, margin=cell_margin)
    return table


def _heading(document, text):
    paragraph = document.add_paragraph()
    paragraph.paragraph_format.space_before = Pt(16)
    paragraph.paragraph_format.space_after = Pt(7)
    run = paragraph.add_run(text)
    run.bold = True
    run.font.name = "Arial"
    run.font.size = Pt(16)
    run.font.color.rgb = RGBColor.from_string(NAVY)
    properties = paragraph._p.get_or_add_pPr()
    borders = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), "8")
    bottom.set(qn("w:space"), "4")
    bottom.set(qn("w:color"), "2563EB")
    borders.append(bottom)
    properties.append(borders)


def _bullet(document, text):
    paragraph = document.add_paragraph(style="List Bullet")
    paragraph.paragraph_format.space_after = Pt(4)
    run = paragraph.add_run(text)
    run.font.name = "Arial"
    run.font.size = Pt(10.5)
    run.font.color.rgb = RGBColor.from_string("000000")


def _status_counts(items):
    return Counter(norm(item["status"]) for item in items)


def _display_owner(value):
    value = norm(value)
    aliases = {
        "samuel kishore kumar": "S. Kishore Kumar",
        "Samuel Kishore Kumar": "S. Kishore Kumar",
        "ajes mini": "Alpa Mori",
        "Ajes Mini": "Alpa Mori",
    }
    return aliases.get(value, value or "Unassigned")


def _add_page_chrome(section, sprint):
    section.header_distance = Inches(0.492)
    section.footer_distance = Inches(0.492)
    header = section.header.paragraphs[0]
    header.alignment = WD_ALIGN_PARAGRAPH.LEFT
    header.paragraph_format.space_after = Pt(0)
    run = header.add_run(f"Jira WSR | {sprint + ' ' if sprint else ''}Weekly Status Report")
    run.font.name = "Arial"
    run.font.size = Pt(6.5)
    run.font.color.rgb = RGBColor.from_string("D1D5DB")
    footer = section.footer.paragraphs[0]
    footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
    footer.paragraph_format.space_before = Pt(0)
    run = footer.add_run(f"{sprint} | Source: Jira CSV export | Page ")
    run.font.name = "Arial"
    run.font.size = Pt(6.5)
    run.font.color.rgb = RGBColor.from_string("D1D5DB")
    field = OxmlElement("w:fldSimple")
    field.set(qn("w:instr"), "PAGE")
    footer._p.append(field)


def _infer_links(story, tasks):
    stop_words = {"task", "dev", "module", "implement", "for", "the", "and", "with", "session", "activity", "log"}
    story_words = {word.lower() for word in norm(story["summary"]).replace("&", " ").replace("(", " ").replace(")", " ").split() if len(word) > 3 and word.lower() not in stop_words}
    matches = []
    for task in tasks:
        task_words = {word.lower() for word in norm(task["summary"]).replace("&", " ").replace("(", " ").replace(")", " ").split() if len(word) > 3 and word.lower() not in stop_words}
        overlap = story_words & task_words
        if len(overlap) >= 2 or ("crashlytics" in overlap and "error" in overlap):
            matches.append(task)
    return matches


def build_docx_report(path, out, sprint="", week="Week not specified", filters=None):
    headers, raw_rows = read_jira_csv(path)
    raw_rows = filter_rows(raw_rows, headers, filters)
    type_column = col(headers, ["Issue Type", "Type"])
    key_column = col(headers, ["Issue key", "Issue Key", "Key", "Ticket"])
    summary_column = col(headers, ["Summary", "Title", "Description"])
    status_column = col(headers, ["Status", "Issue Status"])
    owner_column = col(headers, ["Assignee", "Owner", "Assigned To"])
    link_column = col(headers, ["Issue Links", "Issue Link", "Linked Issues", "Links", "Parent"])
    items = []
    for row in raw_rows:
        issue_type = norm(row.get(type_column, "")) if type_column else "Work Item"
        items.append({
            "key": norm(row.get(key_column, "")),
            "summary": norm(row.get(summary_column, "")),
            "type": issue_type,
            "kind": issue_type.lower(),
            "status": norm(row.get(status_column, "")) or "New / Open",
            "owner": _display_owner(owner(row.get(owner_column, ""))) if owner_column else "Unassigned",
            "links": norm(row.get(link_column, "")) if link_column else "",
        })
    stories = [item for item in items if item["kind"] == "story"]
    tasks = [item for item in items if item["kind"] == "task"]
    all_bugs = [item for item in items if item["kind"] == "bug"]
    bugs = [item for item in all_bugs if kind(item["status"]) != "done"]
    by_key = {item["key"]: item for item in items}
    linked_tasks = defaultdict(list)
    for story in stories:
        for key in story["links"].replace(";", ",").split(","):
            linked = by_key.get(norm(key))
            if linked and linked["kind"] in {"task", "bug"}:
                linked_tasks[story["key"]].append(linked)
    if not link_column:
        for story in stories:
            linked_tasks[story["key"]] = _infer_links(story, tasks)
    task_status = _status_counts(tasks)
    bug_status = _status_counts(all_bugs)
    unassigned = [item for item in items if not item["owner"] or item["owner"] == "Unassigned"]

    document = Document()
    section = document.sections[0]
    section.page_width = Inches(8.5)
    section.page_height = Inches(11)
    section.top_margin = Inches(0.625)
    section.bottom_margin = Inches(0.625)
    section.left_margin = Inches(0.625)
    section.right_margin = Inches(0.625)
    _add_page_chrome(section, sprint)
    normal = document.styles["Normal"]
    normal.font.name = "Arial"
    normal.font.size = Pt(8.5)
    normal.font.color.rgb = RGBColor.from_string(TEXT)

    title = document.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = title.add_run(f"{sprint + ' - ' if sprint else ''}Weekly Status Report")
    run.bold = True
    run.font.name = "Arial"
    run.font.size = Pt(22)
    run.font.color.rgb = RGBColor.from_string(NAVY)
    title.paragraph_format.space_after = Pt(2)
    subtitle = document.add_paragraph()
    subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
    subtitle_run = subtitle.add_run(f"{week}   |   Prepared for stakeholder distribution")
    subtitle_run.italic = True
    subtitle_run.font.name = "Arial"
    subtitle_run.font.size = Pt(11)
    subtitle_run.font.color.rgb = RGBColor.from_string(MUTED)
    subtitle.paragraph_format.space_after = Pt(10)

    alert = document.add_table(rows=1, cols=1)
    alert.alignment = WD_TABLE_ALIGNMENT.LEFT
    _borders(alert, RED)
    _set_table_width(alert)
    message = f"OVERALL STATUS: AT RISK\n{len(stories)} workstreams are represented at the story level. {len(tasks)} tasks are tracked ({task_status['Done']} Done), {len(bugs)} bugs need attention, and {len(unassigned)} items are unassigned."
    _set_cell(alert.cell(0, 0), "!  " + message, color=TEXT, size=8, fill="FEE2E2", margin=140, runs=[
        ("!  OVERALL STATUS: AT RISK\n", True, RED),
        (message.split("\n", 1)[1], False, TEXT),
    ])

    _heading(document, "Sprint Snapshot")
    completion = f"{task_status['Done'] / len(tasks) * 100:.0f}%" if tasks else "0%"
    snapshot_table = _table(document, [[f"{len(stories)}\nUser Stories", f"{completion}\nTasks Complete", f"{len(bugs)}\nOpen Bugs", f"{len(unassigned)}\nUnassigned Items"]], [1.8125] * 4, header=False, body_size=10.5, cell_margin=120, fills=["F3F4F6", "D1FAE5", "FEE2E2", "FEF3C7"])
    snapshot_colors = [TEXT, GREEN, RED, AMBER]
    for index, cell in enumerate(snapshot_table.rows[0].cells):
        value, label = cell.text.split("\n", 1)
        _set_cell(cell, "", size=8, fill=["F3F4F6", "D1FAE5", "FEE2E2", "FEF3C7"][index], margin=120, runs=[
            (value + "\n", True, snapshot_colors[index]),
            (label.upper(), True, MUTED),
        ])
    note = document.add_paragraph(f"{len(tasks)} tasks tracked ({task_status['Done']} Done, {task_status['New / Open']} New/Open, {task_status['In Progress']} In Progress)   |   {len(all_bugs)} bugs tracked")
    note.alignment = WD_ALIGN_PARAGRAPH.CENTER
    note.paragraph_format.space_after = Pt(8)
    for run in note.runs:
        run.font.name = "Arial"
        run.font.size = Pt(9.5)
        run.font.color.rgb = RGBColor.from_string(MUTED)

    _heading(document, "Highlights & Risks")
    panels = document.add_table(rows=1, cols=2)
    panels.alignment = WD_TABLE_ALIGNMENT.LEFT
    _borders(panels)
    _set_table_width(panels)
    highlights = f"What went well\n{task_status['Done']} of {len(tasks)} tasks completed\n{len(stories)} workstreams are visible in the report\nLinked task progress is calculated from the CSV"
    risks = f"Needs attention\n{len(bugs)} bugs remain open\n{len(unassigned)} items are unassigned\n{bug_status['New / Open']} bugs are New/Open and need triage"
    _set_cell(panels.cell(0, 0), highlights, size=10.5, fill="F3F4F6", margin=120, runs=[
        ("What went well\n", True, GREEN),
        ("\n".join(highlights.split("\n")[1:]), False, "000000"),
    ])
    _set_cell(panels.cell(0, 1), risks, size=10.5, fill="FEF2F2", margin=120, runs=[
        ("Needs attention\n", True, RED),
        ("\n".join(risks.split("\n")[1:]), False, "000000"),
    ])

    _heading(document, f"Workstream Progress ({len(stories)} Stories)")
    paragraph = document.add_paragraph("Story-level status is shown alongside actual progress based on linked tasks from the Jira export.")
    paragraph.paragraph_format.space_after = Pt(8)
    for run in paragraph.runs:
        run.font.name = "Arial"
        run.font.size = Pt(10.5)
        run.font.color.rgb = RGBColor.from_string(MUTED)
    workstream_rows = [["Key", "Workstream", "Owner", "Task Progress"]]
    for story in stories:
        linked = [item for item in linked_tasks.get(story["key"], []) if item["kind"] == "task"]
        done = sum(kind(item["status"]) == "done" for item in linked)
        progress = "No linked tasks" if not linked else f"{done}/{len(linked)} ({done / len(linked) * 100:.0f}%)"
        workstream_rows.append([story["key"], story["summary"], story["owner"] or "Unassigned", progress])
    _table(document, workstream_rows, [1.0, 3.75, 1.35, 1.15])

    _heading(document, f"Bugs Needing Attention ({len(bugs)})")
    paragraph = document.add_paragraph("Sorted by status so items closest to closure remain visible alongside active risks.")
    paragraph.paragraph_format.space_after = Pt(8)
    for run in paragraph.runs:
        run.font.name = "Arial"
        run.font.size = Pt(10.5)
        run.font.color.rgb = RGBColor.from_string(MUTED)
    bug_order = {"Ready for Testing": 0, "New / Open": 1, "In Progress": 2, "HerdX Accepted": 3}
    bug_rows = [["Key", "Issue", "Owner", "Status"]]
    for bug in sorted(bugs, key=lambda item: (bug_order.get(item["status"], 9), item["key"])):
        bug_rows.append([bug["key"], bug["summary"], bug["owner"] or "Unassigned", bug["status"]])
    _table(document, bug_rows, [1.0, 3.75, 1.35, 1.15], status_column=3)

    _heading(document, "Workload by Owner")
    grouped = defaultdict(list)
    for item in items:
        grouped[item["owner"] or "Unassigned"].append(item)
    owner_rows = [["Owner", "Items", "Mix", "Note"]]
    for item_owner, owned in sorted(grouped.items(), key=lambda pair: (-len(pair[1]), pair[0])):
        mix = Counter(item["type"] for item in owned)
        mix_text = " - ".join(f"{count} {label}" for label, count in sorted(mix.items()))
        open_count = sum(kind(item["status"]) != "done" for item in owned)
        owner_rows.append([item_owner or "Unassigned", str(len(owned)), mix_text, f"{open_count} open item(s)"])
    owner_table = _table(document, owner_rows, [1.45, 0.65, 2.95, 2.2])
    for row in owner_table.rows[1:]:
        cell = row.cells[0]
        owner_name = cell.text
        _set_cell(cell, owner_name, bold=True, color=RED if owner_name == "Unassigned" else TEXT, size=7.4, margin=60)

    _heading(document, "Next Focus")
    _bullet(document, f"Close or validate the {bug_status['Ready for Testing']} Ready-for-Testing bugs before sprint end.")
    _bullet(document, f"Triage and assign the {len(unassigned)} unassigned items.")
    _bullet(document, "Progress remaining task work and confirm milestones.")
    _bullet(document, "Update story-level statuses in Jira to reflect actual task completion.")
    _heading(document, "Management Attention")
    _bullet(document, f"Review the {len(unassigned)} unassigned active items and assign owners this week.")
    _bullet(document, "Track New/Open bugs closely and confirm their next action.")
    _bullet(document, "Confirm closure paths for accepted or completed work.")

    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    document.save(out)