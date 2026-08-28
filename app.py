import os
from flask import Flask, render_template, request, send_file
from report_generator import build_report
app=Flask(__name__)
@app.get('/')
def index(): return render_template('index.html')
@app.post('/generate')
def generate():
    f=request.files.get('csv_file')
    if not f or not f.filename.lower().endswith('.csv'): return 'Please upload a CSV file.',400
    out='/tmp/jira_weekly_report'; os.makedirs(out,exist_ok=True)
    csv_path=os.path.join(out,'input.csv'); pdf_path=os.path.join(out,'Sprint_Weekly_Status_Report.pdf')
    f.save(csv_path)
    build_report(csv_path,pdf_path,(request.form.get('sprint') or 'Sprint 100').strip(),(request.form.get('week') or 'Week of 17–21 Aug 2026').strip())
    return send_file(pdf_path,as_attachment=True,download_name='Sprint_Weekly_Status_Report.pdf')
if __name__=='__main__': app.run(host='0.0.0.0',port=int(os.environ.get('PORT',5000)),debug=False)
