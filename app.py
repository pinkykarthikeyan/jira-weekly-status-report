from flask import Flask, render_template, request, send_file, flash, redirect, url_for
from report_generator import build_report
import os
import tempfile

app = Flask(__name__)
app.secret_key = "jira-weekly-report-local"

@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")

@app.route("/generate", methods=["POST"])
def generate():
    csv_file = request.files.get("csv_file")
    sprint = request.form.get("sprint", "Sprint 100").strip() or "Sprint 100"
    week = request.form.get("week", "Week of 17–21 Aug 2026").strip() or "Week of 17–21 Aug 2026"

    if not csv_file or not csv_file.filename:
        flash("Please choose a Jira CSV file.")
        return redirect(url_for("index"))

    if not csv_file.filename.lower().endswith(".csv"):
        flash("Please upload a .csv file.")
        return redirect(url_for("index"))

    with tempfile.TemporaryDirectory() as tmp:
        csv_path = os.path.join(tmp, "jira.csv")
        pdf_path = os.path.join(tmp, "Sprint_Weekly_Status_Report.pdf")
        csv_file.save(csv_path)

        try:
            build_report(csv_path, pdf_path, sprint=sprint, week=week)
        except Exception as exc:
            flash(f"Could not generate the PDF: {exc}")
            return redirect(url_for("index"))

        return send_file(
            pdf_path,
            as_attachment=True,
            download_name="Sprint_Weekly_Status_Report.pdf",
            mimetype="application/pdf"
        )

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=False)
