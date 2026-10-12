import os
import tempfile
from datetime import date
from flask import Flask, jsonify, render_template, request, send_file, send_from_directory, abort
from docx_report_generator import build_docx_report, build_production_bug_report
from report_generator import csv_sprint_label, csv_week_label, get_filter_options
from report_data import latest_sample, load_items, sprint_from_filename, summary
from resource_report import build_backlog_report, build_resource_report
app=Flask(__name__)
BASE_DIR=os.path.dirname(os.path.abspath(__file__))

DEFAULT_FROM_DATE=''
DEFAULT_TO_DATE=''

def format_week_label(from_value,to_value):
    if not from_value and not to_value:
        return 'Week not specified'
    if not from_value or not to_value:
        raise ValueError('Please select both From and To dates, or leave both blank.')
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

def _upload_csv(name='csv_file'):
    f=request.files.get(name)
    if not f or not f.filename.lower().endswith('.csv'): return None,None
    out=os.path.join(tempfile.gettempdir(),'jira_weekly_report'); os.makedirs(out,exist_ok=True)
    path=os.path.join(out,f'input_{os.getpid()}_{abs(hash(f.filename))}.csv')
    f.save(path)
    return path,f.filename

def _form_filters():
    return {
        'label':request.form.getlist('label'),
        'sprint':[v.strip() for v in request.form.getlist('sprint') if v.strip()],
        'status':request.form.getlist('status'),
        'workitem_type':request.form.getlist('workitem_type'),
        'from_date':request.form.get('from_date','').strip(),
        'to_date':request.form.get('to_date','').strip(),
    }

@app.get('/')
def dashboard():
    return render_template('dashboard.html',page='dashboard')

@app.get('/wsr')
def wsr_page():
    return render_template('wsr.html',page='wsr',default_from_date=DEFAULT_FROM_DATE,default_to_date=DEFAULT_TO_DATE)

@app.get('/resource')
def resource_page():
    return render_template('resource.html',page='resource',default_from_date=DEFAULT_FROM_DATE,default_to_date=DEFAULT_TO_DATE)

@app.get('/backlog')
def backlog_page():
    return render_template('backlog.html',page='backlog',default_from_date=DEFAULT_FROM_DATE,default_to_date=DEFAULT_TO_DATE)

@app.get('/sample.csv')
def sample_csv():
    path=latest_sample(BASE_DIR)
    if not path: abort(404)
    return send_from_directory(BASE_DIR,os.path.basename(path),mimetype='text/csv')

@app.post('/api/summary')
def api_summary():
    path,filename=_upload_csv()
    if not path: return jsonify(error='Please upload a CSV file.'),400
    try:
        return jsonify(summary(load_items(path),csv_sprint_label(path) or sprint_from_filename(filename)))
    except (OSError,ValueError) as exc:
        return jsonify(error=str(exc)),400
    finally:
        try: os.unlink(path)
        except OSError: pass

def _generate_new_report(builder,download_name):
    path,filename=_upload_csv()
    if not path: return 'Please upload a CSV file.',400
    try:
        from_value=request.form.get('from_date','').strip(); to_value=request.form.get('to_date','').strip()
        try:
            week=format_week_label(from_value,to_value) if from_value or to_value else csv_week_label(path)
        except ValueError as exc:
            return str(exc),400
        sprint=', '.join(v.strip() for v in request.form.getlist('sprint') if v.strip()) or csv_sprint_label(path) or sprint_from_filename(filename)
        out=os.path.join(tempfile.gettempdir(),'jira_weekly_report',f'{os.getpid()}_{download_name}')
        builder(path,out,sprint,week,filters=_form_filters())
        return send_file(out,as_attachment=True,download_name=download_name)
    finally:
        try: os.unlink(path)
        except OSError: pass

@app.post('/generate/resource')
def generate_resource():
    return _generate_new_report(build_resource_report,'Resource_Wise_Sprint_Report.docx')

@app.post('/generate/backlog')
def generate_backlog():
    return _generate_new_report(build_backlog_report,'Product_Backlog_Report.docx')

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
    from_value=request.form.get('from_date','').strip()
    to_value=request.form.get('to_date','').strip()
    try:
        week=format_week_label(from_value,to_value) if from_value or to_value else None
    except ValueError as exc:
        return str(exc),400
    selected_sprints=[value.strip() for value in request.form.getlist('sprint') if value.strip()]
    filters={
        'label':request.form.getlist('label'),
        'sprint':selected_sprints,
        'status':request.form.getlist('status'),
        'workitem_type':request.form.getlist('workitem_type'),
        'from_date':request.form.get('from_date','').strip(),
        'to_date':request.form.get('to_date','').strip(),
    }
    report_sprint=', '.join(selected_sprints)
    report_type=request.form.get('report_type','wsr').strip().lower()
    out=os.path.join(tempfile.gettempdir(),'jira_weekly_report'); os.makedirs(out,exist_ok=True)
    csv_path=os.path.join(out,'input.csv')
    f.save(csv_path)
    week=week or csv_week_label(csv_path)
    report_sprint=report_sprint or csv_sprint_label(csv_path) or sprint_from_filename(f.filename)
    if report_type=='production':
        report_docx=os.path.join(out,'Production_Bug_Status_Report.docx')
        build_production_bug_report(csv_path,report_docx,report_sprint,week,filters=filters)
        return send_file(report_docx,as_attachment=True,download_name='Production_Bug_Status_Report.docx')
    report_docx=os.path.join(out,'Jira_Status_Report.docx')
    build_docx_report(csv_path,report_docx,report_sprint,week,filters=filters)
    return send_file(report_docx,as_attachment=True,download_name='Jira_Status_Report.docx')
if __name__=='__main__': app.run(host='0.0.0.0',port=int(os.environ.get('PORT',5000)),debug=False)
