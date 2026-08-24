# Jira Weekly Status Report Generator

A local Flask application for VS Code that accepts a Jira CSV and generates a 2-page A4 PDF similar to the supplied stakeholder-report reference.

## Requirements

- Windows 10/11
- Python 3.10+ (3.11 or 3.12 recommended)
- VS Code

## Run in VS Code

Open the project folder in VS Code, then open **Terminal → New Terminal**.

### 1. Create a virtual environment

Windows PowerShell:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, use:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

### 2. Install packages

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Start the application

```powershell
python app.py
```

You should see Flask running at:

`http://127.0.0.1:5000`

Open that address in Chrome/Edge.

### 4. Generate the PDF

1. Select your Jira CSV.
2. Enter Sprint (for example `Sprint 100`).
3. Enter the week/date range.
4. Click **Generate & Download PDF**.

The browser downloads:

`Sprint_Weekly_Status_Report.pdf`

## CSV columns

The application auto-detects common Jira headers:

- Issue Type
- Issue key / Issue Key / Key
- Summary
- Status
- Assignee / Owner / Assigned To

It also scans CSV cells for Jira issue keys such as `HA30-15004` to build the User Story → Task/Bug detail page.

## Layout

The PDF is A4 portrait and contains:

### Page 1
- Weekly Status Report title
- Sprint/date
- Four metric cards
- Overall status banner
- Three equal-height information panels
- All User Stories snapshot

### Page 2
- Detailed Delivery Status
- User Story → linked Tasks/Bugs
- Done / In Progress / New/Open / Open legend

The generator uses ReportLab and does not require Microsoft Office or Excel.

## Important

The two name corrections requested for the reference report are included in the generator:

- Samuel Ruthra Kumar → Samuel Kishore Kumar
- Ajes Mini → Alpa Mori

If your future Jira CSV uses different owner values, edit `owner_correction()` in `report_generator.py`.


## Free deployment on Render

This project is Render-ready.

1. Create a GitHub repository and upload all project files.
2. In Render, choose **New → Web Service** and connect the GitHub repository.
3. Select the **Free** instance.
4. Render can use the included `render.yaml`, or enter:
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn app:app`
5. Deploy. Render provides an HTTPS `onrender.com` URL.

Render's free web service can spin down after 15 minutes of inactivity, so the first request after idle time can take about a minute. The service filesystem is also ephemeral, which is fine for this app because the uploaded CSV is processed into a PDF in memory/temp storage and the generated file is returned to the browser.
