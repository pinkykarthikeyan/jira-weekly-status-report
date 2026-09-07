# Jira Weekly Status Report Generator

The PDF layout is constrained to the printable A4 width. KPI cards are equal width, insight panels are equal width/height, and all table columns fit inside the page margins. The web form generates one PDF containing only the Jira work items that match the selected filters. The generator still supports separate backlog and production reports programmatically.

## VS Code
`py -3 -m venv .venv`
`.\.venv\Scripts\Activate.ps1`
`pip install -r requirements.txt`
`python app.py`

Open http://127.0.0.1:5000. Select the From and To dates, then choose any available label, sprint, status, or work item type from the CSV-driven multi-select lists. The download is one filtered PDF.

## Render
Build: `pip install -r requirements.txt`
Start: `gunicorn app:app`
