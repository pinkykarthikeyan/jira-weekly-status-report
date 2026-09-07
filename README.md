# Jira Weekly Status Report Generator

The PDF layout is constrained to the printable A4 width. KPI cards are equal width, insight panels are equal width/height, and all table columns fit inside the page margins. The generator creates two separate PDFs: a product-backlog report for work without the `prod` or `firebase` labels, and a production-ticket report for work with either exact label.

## VS Code
`py -3 -m venv .venv`
`.\.venv\Scripts\Activate.ps1`
`pip install -r requirements.txt`
`python app.py`

Open http://127.0.0.1:5000. Select the From and To dates, then choose any available label, sprint, status, or work item type from the CSV-driven dropdowns. The download is a ZIP containing both PDFs.

## Render
Build: `pip install -r requirements.txt`
Start: `gunicorn app:app`
