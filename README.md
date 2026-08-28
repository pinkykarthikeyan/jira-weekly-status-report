# Jira Weekly Status Report Generator

The PDF layout is constrained to the printable A4 width. KPI cards are equal width, insight panels are equal width/height, and all table columns fit inside the page margins.

## VS Code
`py -3 -m venv .venv`
`.\.venv\Scripts\Activate.ps1`
`pip install -r requirements.txt`
`python app.py`

Open http://127.0.0.1:5000

## Render
Build: `pip install -r requirements.txt`
Start: `gunicorn app:app`
