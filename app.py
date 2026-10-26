import os
import tempfile
from datetime import date
from io import BytesIO
from flask import Flask, jsonify, render_template, request, send_file, send_from_directory, abort
from docx_report_generator import build_production_bug_report
from report_generator import csv_sprint_label, csv_week_label, get_filter_options
from report_data import latest_sample, load_items, sprint_from_filename, summary
from resource_report import build_backlog_report, build_resource_report
from wsr_report import build_wsr_report
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
        return f'Week of {start.day} {start:%B %Y}'
    return f'Week of {start.day} {start:%B %Y}-{end.day} {end:%B %Y}'

def _upload_csv(name='csv_file'):
    f=request.files.get(name)
    if not f or not f.filename.lower().endswith('.csv'): return None,None
    fd,path=tempfile.mkstemp(suffix='.csv')
    os.close(fd)
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
    fd,out=tempfile.mkstemp(suffix='.docx')
    os.close(fd)
    try:
        from_value=request.form.get('from_date','').strip(); to_value=request.form.get('to_date','').strip()
        week=format_week_label(from_value,to_value) if from_value or to_value else csv_week_label(path)
        sprint=', '.join(v.strip() for v in request.form.getlist('sprint') if v.strip()) or csv_sprint_label(path) or sprint_from_filename(filename)
        builder(path,out,sprint,week,filters=_form_filters())
        with open(out,'rb') as f: data=BytesIO(f.read())
    except (OSError,ValueError) as exc:
        return str(exc),400
    finally:
        for p in (path,out):
            try: os.unlink(p)
            except OSError: pass
    if callable(download_name): download_name=download_name(sprint)
    return send_file(data,as_attachment=True,download_name=download_name,
                     mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document')

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
    if request.form.get('report_type','wsr').strip().lower()=='production':
        return _generate_new_report(build_production_bug_report,'Production_Bug_Status_Report.docx')
    return _generate_new_report(build_wsr_report,lambda sprint:f"{sprint.replace(' ','_').replace(',','')}_WSR.docx" if sprint else 'Weekly_Status_Report.docx')

if __name__=='__main__': app.run(host='0.0.0.0',port=int(os.environ.get('PORT',5000)),debug=False)
