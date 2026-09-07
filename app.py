import os
import tempfile
import zipfile
from flask import Flask, render_template, request, send_file
from report_generator import build_reports
app=Flask(__name__)
@app.get('/')
def index(): return render_template('index.html')
@app.post('/generate')
def generate():
    f=request.files.get('csv_file')
    if not f or not f.filename.lower().endswith('.csv'): return 'Please upload a CSV file.',400
    out=os.path.join(tempfile.gettempdir(),'jira_weekly_report'); os.makedirs(out,exist_ok=True)
    csv_path=os.path.join(out,'input.csv')
    backlog_pdf=os.path.join(out,'Product_Backlog_Report.pdf')
    production_pdf=os.path.join(out,'Production_Ticket_Report.pdf')
    zip_path=os.path.join(out,'Jira_Weekly_Status_Reports.zip')
    f.save(csv_path)
    build_reports(csv_path,backlog_pdf,production_pdf,(request.form.get('sprint') or 'Sprint 101').strip(),(request.form.get('week') or 'Week of 17–21 Aug 2026').strip())
    with zipfile.ZipFile(zip_path,'w',zipfile.ZIP_DEFLATED) as archive:
        archive.write(backlog_pdf,arcname='Product_Backlog_Report.pdf')
        archive.write(production_pdf,arcname='Production_Ticket_Report.pdf')
    return send_file(zip_path,as_attachment=True,download_name='Jira_Weekly_Status_Reports.zip')
if __name__=='__main__': app.run(host='0.0.0.0',port=int(os.environ.get('PORT',5000)),debug=False)
