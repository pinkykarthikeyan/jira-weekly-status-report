import fs from "node:fs/promises";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const csvPath = "C:/Users/PinkyAhmed/Downloads/sprint_101_status_updated.csv";
const outputDir = "C:/work/jira-weekly-status-report/outputs/sprint_101_wsr";
const outputPath = `${outputDir}/sprint_101_jira_engineering_wsr.xlsx`;
const previewSummaryPath = `${outputDir}/preview_summary.png`;
const previewActivePath = `${outputDir}/preview_active.png`;
const fontFamily = "Arial";

function parseCsv(text) {
  const rows = [];
  let row = [];
  let field = "";
  let inQuotes = false;
  for (let i = 0; i < text.length; i += 1) {
    const ch = text[i];
    if (inQuotes) {
      if (ch === '"') {
        if (text[i + 1] === '"') {
          field += '"';
          i += 1;
        } else {
          inQuotes = false;
        }
      } else {
        field += ch;
      }
    } else if (ch === '"') {
      inQuotes = true;
    } else if (ch === ",") {
      row.push(field);
      field = "";
    } else if (ch === "\n") {
      row.push(field.replace(/\r$/, ""));
      rows.push(row);
      row = [];
      field = "";
    } else {
      field += ch;
    }
  }
  if (field.length > 0 || row.length > 0) {
    row.push(field.replace(/\r$/, ""));
    rows.push(row);
  }
  return rows;
}

function normalizeRows(csvText) {
  const parsed = parseCsv(csvText);
  const issueTypes = new Set(["Bug", "Task", "Story", "Improvement"]);
  return parsed.slice(1).filter((r) => r.length > 0 && r[0]).map((raw) => {
    const issueTypeIndex = raw.findIndex((v, idx) => idx > 0 && issueTypes.has(v.trim()));
    if (issueTypeIndex < 0) throw new Error(`Could not locate issue type for ${raw[0]}`);
    return {
      Key: raw[0].trim(),
      Summary: raw.slice(1, issueTypeIndex).join(",").trim(),
      "Issue Type": raw[issueTypeIndex].trim(),
      Assignee: (raw[issueTypeIndex + 1] ?? "").trim(),
      Status: (raw[issueTypeIndex + 2] ?? "").trim(),
      Labels: raw.slice(issueTypeIndex + 3, -1).join(",").trim(),
      "Production Bug": (raw[raw.length - 1] ?? "").trim(),
    };
  });
}

function formula(sheetName, address) {
  return `'${sheetName}'!${address.replaceAll("${dataLastRow}", String(dataLastRow))}`;
}

function nextStep(issue) {
  if (issue["Production Bug"] === "Yes") {
    if (issue.Status === "Ready for Testing") return "Complete production validation";
    if (issue.Status === "New / Open") return "Triage and prioritize production fix";
    if (issue.Status === "In Progress") return "Continue production fix";
    if (issue.Status === "HerdX Accepted") return "Confirm disposition and close";
    if (issue.Status === "Cannot Reproduce") return "Confirm reproduction outcome";
  }
  if (!issue.Assignee) return "Assign owner";
  if (issue.Status === "New / Open") return "Triage and plan";
  if (issue.Status === "In Progress") return "Continue development";
  if (issue.Status === "Ready for Testing") return "Complete QA validation";
  if (issue.Status === "HerdX Accepted") return "Confirm acceptance and close";
  if (issue.Status === "Cannot Reproduce") return "Confirm reproduction outcome";
  if (issue.Status === "Rejected / Not a Bug") return "Confirm closure";
  return "Review next action";
}

const csvText = await fs.readFile(csvPath, "utf8");
const records = normalizeRows(csvText);
const sourceHeaders = ["Key", "Summary", "Issue Type", "Assignee", "Status", "Labels", "Production Bug"];
const sourceMatrix = [sourceHeaders, ...records.map((r) => sourceHeaders.map((h) => r[h]))];
const dataLastRow = records.length + 1;

const statusOrder = {
  "New / Open": 0,
  "In Progress": 1,
  "Ready for Testing": 2,
  "HerdX Accepted": 3,
  "Cannot Reproduce": 4,
  "Rejected / Not a Bug": 5,
  "Discarded": 6,
};
const activeRecords = records.filter((r) => r.Status !== "Done").sort((a, b) => {
  const prodDiff = (b["Production Bug"] === "Yes" ? 1 : 0) - (a["Production Bug"] === "Yes" ? 1 : 0);
  if (prodDiff) return prodDiff;
  const statusDiff = (statusOrder[a.Status] ?? 99) - (statusOrder[b.Status] ?? 99);
  if (statusDiff) return statusDiff;
  return a.Key.localeCompare(b.Key);
});

const workbook = Workbook.create();
const summary = workbook.worksheets.add("Jira WSR");
const active = workbook.worksheets.add("Active Issues");
const source = workbook.worksheets.add("Source Data");

for (const sheet of [summary, active, source]) {
  sheet.showGridLines = false;
}
summary.tabColor = "#1F4E78";
active.tabColor = "#5B9BD5";
source.tabColor = "#A5A5A5";

// Source data tab
source.getRange(`A1:G${dataLastRow}`).values = sourceMatrix;
source.getRange("A1:G1").format = {
  fill: "#1F4E78",
  font: { name: fontFamily, bold: true, color: "#FFFFFF", size: 10 },
  horizontalAlignment: "center",
  verticalAlignment: "center",
};
source.getRange(`A2:G${dataLastRow}`).format = {
  font: { name: fontFamily, size: 10, color: "#1F2937" },
  verticalAlignment: "center",
};
source.getRange(`B2:B${dataLastRow}`).format.wrapText = true;
source.getRange(`F2:F${dataLastRow}`).format.wrapText = true;
source.getRange(`A1:G${dataLastRow}`).format.borders = { preset: "outside", style: "thin", color: "#D9E2F3" };
source.getRange("A:A").format.columnWidth = 14;
source.getRange("B:B").format.columnWidth = 62;
source.getRange("C:C").format.columnWidth = 16;
source.getRange("D:D").format.columnWidth = 24;
source.getRange("E:E").format.columnWidth = 22;
source.getRange("F:F").format.columnWidth = 34;
source.getRange("G:G").format.columnWidth = 16;
source.getRange("1:1").format.rowHeight = 24;
source.freezePanes.freezeRows(1);
source.freezePanes.freezeColumns(1);
source.tables.add(`A1:G${dataLastRow}`, true, "SourceDataTable");

// Active issue detail tab
const activeHeaders = ["Key", "Summary", "Issue Type", "Assignee", "Status", "Labels", "Production Bug", "Attention", "Next Step"];
const activeMatrix = [activeHeaders, ...activeRecords.map((r) => [
  r.Key,
  r.Summary,
  r["Issue Type"],
  r.Assignee,
  r.Status,
  r.Labels,
  r["Production Bug"],
  r["Production Bug"] === "Yes" ? "Production risk" : (!r.Assignee ? "Owner needed" : r.Status),
  nextStep(r),
])];
const activeLastRow = activeRecords.length + 5;
active.getRange("A2").values = [["ACTIVE ISSUES"]];
active.getRange("A2").format.font = { name: fontFamily, size: 16, bold: true, color: "#1F2937" };
active.getRange("A3").values = [["All records with Status other than Done, sorted with production bugs first. Use this tab for the detailed In Progress and at-risk view."]];
active.getRange("A3:I3").format.font = { name: fontFamily, size: 10, italic: true, color: "#5B6573" };
active.getRange(`A5:I${activeLastRow}`).values = activeMatrix;
active.getRange("A5:I5").format = {
  fill: "#1F4E78",
  font: { name: fontFamily, bold: true, color: "#FFFFFF", size: 10 },
  horizontalAlignment: "center",
  verticalAlignment: "center",
};
active.getRange(`A6:I${activeLastRow}`).format = {
  font: { name: fontFamily, size: 10, color: "#1F2937" },
  verticalAlignment: "center",
};
active.getRange(`B6:B${activeLastRow}`).format.wrapText = true;
active.getRange(`F6:F${activeLastRow}`).format.wrapText = true;
active.getRange(`I6:I${activeLastRow}`).format.wrapText = true;
active.getRange(`A5:I${activeLastRow}`).format.borders = { preset: "outside", style: "thin", color: "#D9E2F3" };
active.getRange("A:A").format.columnWidth = 14;
active.getRange("B:B").format.columnWidth = 62;
active.getRange("C:C").format.columnWidth = 16;
active.getRange("D:D").format.columnWidth = 24;
active.getRange("E:E").format.columnWidth = 22;
active.getRange("F:F").format.columnWidth = 34;
active.getRange("G:G").format.columnWidth = 16;
active.getRange("H:H").format.columnWidth = 18;
active.getRange("I:I").format.columnWidth = 34;
active.getRange("5:5").format.rowHeight = 26;
active.freezePanes.freezeRows(5);
active.freezePanes.freezeColumns(1);
active.tables.add(`A5:I${activeLastRow}`, true, "ActiveIssuesTable");
active.getRange(`E6:E${activeLastRow}`).conditionalFormats.add("containsText", { text: "New / Open", format: { fill: "#FCE4D6", font: { color: "#9C0006", bold: true } } });
active.getRange(`E6:E${activeLastRow}`).conditionalFormats.add("containsText", { text: "In Progress", format: { fill: "#FFF2CC", font: { color: "#7F6000", bold: true } } });
active.getRange(`E6:E${activeLastRow}`).conditionalFormats.add("containsText", { text: "Ready for Testing", format: { fill: "#DDEBF7", font: { color: "#1F4E78", bold: true } } });
active.getRange(`G6:G${activeLastRow}`).conditionalFormats.add("containsText", { text: "Yes", format: { fill: "#F4CCCC", font: { color: "#9C0006", bold: true } } });
active.getRange(`H6:H${activeLastRow}`).conditionalFormats.add("containsText", { text: "Owner needed", format: { fill: "#FFF2CC", font: { color: "#7F6000", bold: true } } });

// Primary WSR summary tab
summary.getRange("A2").values = [["WEEKLY ENGINEERING STATUS REPORT"]];
summary.getRange("A2").format.font = { name: fontFamily, size: 16, bold: true, color: "#1F2937" };
summary.getRange("A3").values = [["Sprint 101 status extract | Source: sprint_101_status_updated.csv"]];
summary.getRange("A3").format.font = { name: fontFamily, size: 10, italic: true, color: "#5B6573" };
summary.getRange("A5:B8").values = [
  ["Report period", "Sprint 101"],
  ["Team", "HA30 Engineering"],
  ["Overall status", "Amber"],
  ["As of", new Date("2026-09-08T00:00:00Z")],
];
summary.getRange("A5:A8").format.font = { name: fontFamily, size: 10, bold: true, color: "#5B6573" };
summary.getRange("B5:B8").format.font = { name: fontFamily, size: 10, color: "#1F2937" };
summary.getRange("B7").format = { fill: "#FFF2CC", font: { name: fontFamily, size: 10, bold: true, color: "#7F6000" }, horizontalAlignment: "center" };
summary.getRange("B8").format.numberFormat = "yyyy-mm-dd";
summary.getRange("D5:H8").values = [["Status rationale", "Amber reflects 98 non-Done issues and 15 active production bugs.", null, null, null], [null, null, null, null, null], [null, null, null, null, null], [null, null, null, null, null]];
summary.getRange("D5").format.font = { name: fontFamily, size: 10, bold: true, color: "#5B6573" };
summary.getRange("E5:H5").format = { fill: "#F3F6FA", font: { name: fontFamily, size: 10, color: "#1F2937" }, wrapText: true, verticalAlignment: "center" };
summary.getRange("E5:H5").merge();
summary.getRange("E5").values = [["Amber reflects 98 non-Done issues and 15 active production bugs."]];

function band(rangeAddress, text) {
  const range = summary.getRange(rangeAddress);
  range.merge();
  range.values = [[text]];
  range.format = {
    fill: "#D9EAF7",
    font: { name: fontFamily, size: 11, bold: true, color: "#1F2937" },
    borders: { preset: "outside", style: "thin", color: "#9FBAD0" },
  };
}
function header(rangeAddress) {
  summary.getRange(rangeAddress).format = {
    fill: "#1F4E78",
    font: { name: fontFamily, size: 10, bold: true, color: "#FFFFFF" },
    horizontalAlignment: "center",
    verticalAlignment: "center",
  };
}

const s = "Source Data";
band("A10:D10", "1. Completed This Week");
summary.getRange("A11:B17").values = [
  ["Metric", "Value"],
  ["Total issues in extract", null],
  ["Done", null],
  ["Completion rate", null],
  ["Production bugs total", null],
  ["Production bugs still active", null],
  ["Active issues", null],
];
header("A11:B11");
summary.getRange("B12:B17").formulas = [
  [`=COUNTA(${formula(s, "$A$2:$A$${dataLastRow}")})`],
  [`=COUNTIF(${formula(s, "$E$2:$E$${dataLastRow}")},"Done")`],
  ["=B13/B12"],
  [`=COUNTIF(${formula(s, "$G$2:$G$${dataLastRow}")},"Yes")`],
  [`=COUNTIFS(${formula(s, "$G$2:$G$${dataLastRow}")},"Yes",${formula(s, "$E$2:$E$${dataLastRow}")},"<>Done")`],
  [`=COUNTIF(${formula(s, "$E$2:$E$${dataLastRow}")},"<>Done")`],
];
summary.getRange("B14").format.numberFormat = "0.0%";
summary.getRange("A11:B17").format.borders = { preset: "outside", style: "thin", color: "#D9E2F3" };
summary.getRange("B12:B17").format = { fill: "#F3F6FA", font: { name: fontFamily, size: 10, bold: true, color: "#1F2937" }, horizontalAlignment: "right" };

summary.getRange("D11:E17").values = [
  ["Issue type", "Count"],
  ["Bug", null],
  ["Task", null],
  ["Story", null],
  ["Improvement", null],
  ["Deployment-tagged", null],
  ["QA automation", null],
];
header("D11:E11");
summary.getRange("E12:E15").formulas = [
  [`=COUNTIF(${formula(s, "$C$2:$C$${dataLastRow}")},"Bug")`],
  [`=COUNTIF(${formula(s, "$C$2:$C$${dataLastRow}")},"Task")`],
  [`=COUNTIF(${formula(s, "$C$2:$C$${dataLastRow}")},"Story")`],
  [`=COUNTIF(${formula(s, "$C$2:$C$${dataLastRow}")},"Improvement")`],
];
summary.getRange("E16:E17").values = [[12], [10]];
summary.getRange("D11:E17").format.borders = { preset: "outside", style: "thin", color: "#D9E2F3" };
summary.getRange("E12:E17").format = { fill: "#F3F6FA", font: { name: fontFamily, size: 10, bold: true, color: "#1F2937" }, horizontalAlignment: "right" };

band("A20:D20", "2. In Progress");
summary.getRange("A21:D29").values = [
  ["Status", "Issue count", "Production bugs", "Share of extract"],
  ["New / Open", null, null, null],
  ["In Progress", null, null, null],
  ["Ready for Testing", null, null, null],
  ["HerdX Accepted", null, null, null],
  ["Rejected / Not a Bug", null, null, null],
  ["Cannot Reproduce", null, null, null],
  ["Discarded", null, null, null],
  ["Total not Done", null, null, null],
];
header("A21:D21");
const statusRows = [22, 23, 24, 25, 26, 27, 28];
for (const rowNum of statusRows) {
  summary.getRange(`B${rowNum}`).formulas = [[`=COUNTIF(${formula(s, "$E$2:$E$${dataLastRow}")},A${rowNum})`]];
  summary.getRange(`C${rowNum}`).formulas = [[`=COUNTIFS(${formula(s, "$E$2:$E$${dataLastRow}")},A${rowNum},${formula(s, "$G$2:$G$${dataLastRow}")},"Yes")`]];
  summary.getRange(`D${rowNum}`).formulas = [[`=B${rowNum}/$B$12`]];
}
summary.getRange("B29").formulas = [["=SUM(B22:B28)"]];
summary.getRange("C29").formulas = [["=SUM(C22:C28)"]];
summary.getRange("D29").formulas = [["=B29/$B$12"]];
summary.getRange("D22:D29").format.numberFormat = "0.0%";
summary.getRange("A21:D29").format.borders = { preset: "outside", style: "thin", color: "#D9E2F3" };
summary.getRange("A29:D29").format = { fill: "#F3F6FA", font: { name: fontFamily, size: 10, bold: true, color: "#1F2937" } };

band("A32:D32", "3. Blocked or At Risk");
summary.getRange("A33:C38").values = [
  ["Risk / issue", "Count", "Action / reference"],
  ["Active production bugs", null, "See Active Issues tab; production risks are sorted first."],
  ["New / Open issues", null, "Triage and plan."],
  ["In Progress issues", null, "Continue development and confirm next milestones."],
  ["Ready for Testing", null, "Complete QA validation."],
  ["Unassigned active issues", null, "Assign owners; see Attention column."],
];
header("A33:C33");
summary.getRange("B34:B37").formulas = [
  ["=B16"],
  ["=B22"],
  ["=B23"],
  ["=B24"],
];
summary.getRange("B38").values = [[5]];
summary.getRange("A33:C38").format.borders = { preset: "outside", style: "thin", color: "#D9E2F3" };
summary.getRange("B34:B38").format = { fill: "#FFF2CC", font: { name: fontFamily, size: 10, bold: true, color: "#7F6000" }, horizontalAlignment: "right" };
summary.getRange("C34:C38").format.wrapText = true;

band("A41:D41", "4. Release / Deployment Updates");
summary.getRange("A42:C46").values = [
  ["Metric", "Count", "Notes"],
  ["Deployment-tagged issues", null, "Includes release and deployment work."],
  ["Deployment-tagged Done", null, "Completed deployment items in the extract."],
  ["Deployment-tagged still open", null, "Follow up on remaining deployment work."],
  ["QA automation still open", null, "Regression items not yet Done."],
];
header("A42:C42");
summary.getRange("B43:B46").values = [[12], [10], [2], [2]];
summary.getRange("A42:C46").format.borders = { preset: "outside", style: "thin", color: "#D9E2F3" };
summary.getRange("C43:C46").format.wrapText = true;

band("A49:D49", "5. Next Week's Focus");
summary.getRange("A50:C53").values = [
  ["Focus area", "Recommended action", "Basis"],
  ["Production defects", "Prioritize active production bugs and confirm ownership.", "15 active production bugs"],
  ["Testing pipeline", "Close or retest items currently Ready for Testing.", "16 Ready for Testing"],
  ["Open backlog", "Triage New / Open items and assign the unowned work.", "38 New / Open; 5 unassigned active issues"],
];
header("A50:C50");
summary.getRange("A50:C53").format.borders = { preset: "outside", style: "thin", color: "#D9E2F3" };
summary.getRange("B51:C53").format.wrapText = true;

summary.getRange("A56").values = [["Source note: The CSV contains issue status, ownership, labels, and production-bug flags, but no issue dates, estimates, due dates, or sprint timestamps. Counts therefore reflect the supplied Sprint 101 extract rather than a dated weekly delta."]];
summary.getRange("A56:H56").merge();
summary.getRange("A56:H56").format = { fill: "#F3F6FA", font: { name: fontFamily, size: 9, italic: true, color: "#5B6573" }, wrapText: true, verticalAlignment: "center" };

summary.getRange("A:A").format.columnWidth = 28;
summary.getRange("B:B").format.columnWidth = 22;
summary.getRange("C:C").format.columnWidth = 30;
summary.getRange("D:D").format.columnWidth = 18;
summary.getRange("E:E").format.columnWidth = 14;
summary.getRange("F:H").format.columnWidth = 14;
summary.getRange("56:56").format.rowHeight = 36;
summary.getRange("A2:H56").format.verticalAlignment = "center";
summary.getRange("B12:B17").format.horizontalAlignment = "right";
summary.getRange("B22:D29").format.horizontalAlignment = "right";
summary.getRange("B34:B38").format.horizontalAlignment = "right";
summary.getRange("B43:B46").format.horizontalAlignment = "right";

workbook.recalculate();

const check = await workbook.inspect({
  kind: "table",
  sheetId: "Jira WSR",
  range: "A2:H56",
  include: "values,formulas",
  tableMaxRows: 60,
  tableMaxCols: 8,
  maxChars: 12000,
});
console.log(check.ndjson);
const errors = await workbook.inspect({
  kind: "match",
  searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!",
  options: { useRegex: true, maxResults: 300 },
  summary: "final formula error scan",
});
console.log(errors.ndjson);

await fs.mkdir(outputDir, { recursive: true });
const summaryPreview = await workbook.render({ sheetName: "Jira WSR", range: "A1:H56", scale: 1, format: "png" });
await fs.writeFile(previewSummaryPath, new Uint8Array(await summaryPreview.arrayBuffer()));
const activePreview = await workbook.render({ sheetName: "Active Issues", range: "A1:I25", scale: 1, format: "png" });
await fs.writeFile(previewActivePath, new Uint8Array(await activePreview.arrayBuffer()));
const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(outputPath);
console.log(JSON.stringify({ outputPath, recordCount: records.length, activeCount: activeRecords.length, dataLastRow, activeLastRow }));
