(function(){
var KEY='jira_csv_v1';
var csvFile=document.getElementById('csv_file');
if(!csvFile)return;
var fromDate=document.getElementById('from_date'),toDate=document.getElementById('to_date'),statusEl=document.getElementById('filter_status');
function syncDates(){if(!fromDate||!toDate)return;if(fromDate.value)toDate.min=fromDate.value;else toDate.removeAttribute('min');if(toDate.value&&fromDate.value&&toDate.value<fromDate.value)toDate.value=fromDate.value}
function fill(id,values){var s=document.getElementById(id);if(!s)return;s.innerHTML='';values.forEach(function(v){s.add(new Option(v,v))});s.disabled=false}
function load(){
  if(!csvFile.files[0])return;
  statusEl.textContent='Loading filter options…';
  var d=new FormData();d.append('csv_file',csvFile.files[0]);
  fetch('/filter-options',{method:'POST',body:d}).then(function(r){return r.json().then(function(o){if(!r.ok)throw new Error(o.error||'Unable to load filter options.');return o})}).then(function(o){
    fill('label',o.labels);fill('sprint',o.sprints);fill('status',o.statuses);fill('workitem_type',o.workitem_types);
    statusEl.textContent='Select one or more values. Leave a list empty to include all values. Leave dates blank to include all dates.';
  }).catch(function(e){statusEl.textContent=e.message});
}
// Remember the CSV for this browser tab so every page can reuse it.
function remember(file){var r=new FileReader();r.onload=function(){try{sessionStorage.setItem(KEY,JSON.stringify({name:file.name,text:r.result}))}catch(e){}};r.readAsText(file)}
csvFile.addEventListener('change',function(){if(csvFile.files[0])remember(csvFile.files[0]);load()});
if(fromDate)fromDate.addEventListener('change',syncDates);syncDates();
try{var saved=JSON.parse(sessionStorage.getItem(KEY)||'null');
  if(saved&&window.DataTransfer){var dt=new DataTransfer();dt.items.add(new File([saved.text],saved.name,{type:'text/csv'}));csvFile.files=dt.files;statusEl.textContent='Using '+saved.name+' from the dashboard. Choose another file to replace it.';load()}}catch(e){}
})();
