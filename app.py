import os
import tempfile
import zipfile
from datetime import date
from flask import Flask, jsonify, render_template, request, send_file
from report_generator import build_reports, get_filter_options
app=Flask(__name__)

DEFAULT_FROM_DATE='2026-08-17'
DEFAULT_TO_DATE='2026-08-21'

def format_week_label(from_value,to_value):
    try:
        start=date.fromisoformat(from_value)
        end=date.fromisoformat(to_value)
    except (TypeError,ValueError) as exc:
        raise ValueError('Please select valid From and To dates.') from exc
    if end < start:
        raise ValueError('The To date must be on or after the From date.')
    if start == end:
        return f'Week of {start.day} {start.strftime("%b")} {start.year}'
    if start.year == end.year and start.month == end.month:
        return f'Week of {start.day}–{end.day} {end.strftime("%b")} {end.year}'
    if start.year == end.year:
        return f'Week of {start.day} {start.strftime("%b")}–{end.day} {end.strftime("%b")} {end.year}'
    return f'Week of {start.day} {start.strftime("%b")} {start.year}–{end.day} {end.strftime("%b")} {end.year}'

@app.get('/')
def index():
    return render_template('index.html',default_from_date=DEFAULT_FROM_DATE,default_to_date=DEFAULT_TO_DATE)

@app.post('/filter-options')
def filter_options():
    f=request.files.get('csv_file')
    if not f or not f.filename.lower().endswith('.csv'):
        return jsonify(error='Please upload a CSV file.'),400
    temp_path=None
    try:
        with tempfile.NamedTemporaryFile(suffix='.csv',delete=False) as temp:
            temp_path=temp.name
        f.save(temp_path)
        return jsonify(get_filter_options(temp_path))
    except (OSError,ValueError) as exc:
        return jsonify(error=str(exc)),400
    finally:
        if temp_path:
            try:
                os.unlink(temp_path)
            except FileNotFoundError:
                pass

@app.post('/generate')
def generate():
    f=request.files.get('csv_file')
    if not f or not f.filename.lower().endswith('.csv'): return 'Please upload a CSV file.',400
    try:
        week=format_week_label(request.form.get('from_date'),request.form.get('to_date'))
    except ValueError as exc:
        return str(exc),400
    selected_sprint=(request.form.get('sprint') or '').strip()
    filters={
        'label':(request.form.get('label') or '').strip(),
        'sprint':selected_sprint,
        'status':(request.form.get('status') or '').strip(),
        'workitem_type':(request.form.get('workitem_type') or '').strip(),
    }
    out=os.path.join(tempfile.gettempdir(),'jira_weekly_report'); os.makedirs(out,exist_ok=True)
    csv_path=os.path.join(out,'input.csv')
    backlog_pdf=os.path.join(out,'Product_Backlog_Report.pdf')
    production_pdf=os.path.join(out,'Production_Ticket_Report.pdf')
    zip_path=os.path.join(out,'Jira_Weekly_Status_Reports.zip')
    f.save(csv_path)
    build_reports(csv_path,backlog_pdf,production_pdf,selected_sprint or 'All Sprints',week,filters=filters)
    with zipfile.ZipFile(zip_path,'w',zipfile.ZIP_DEFLATED) as archive:
        archive.write(backlog_pdf,arcname='Product_Backlog_Report.pdf')
        archive.write(production_pdf,arcname='Production_Ticket_Report.pdf')
    return send_file(zip_path,as_attachment=True,download_name='Jira_Weekly_Status_Reports.zip')
if __name__=='__main__': app.run(host='0.0.0.0',port=int(os.environ.get('PORT',5000)),debug=False)
