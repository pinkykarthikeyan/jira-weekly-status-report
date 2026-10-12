(function(){
var KEY='jira_csv_v1',COLORS={Done:'var(--done)',Testing:'var(--test)','In Progress':'var(--prog)',Open:'var(--open)',Dropped:'var(--drop)'},ORDER=['Done','Testing','In Progress','Open','Dropped'];
var $=function(id){return document.getElementById(id)};
function el(tag,cls,text){var e=document.createElement(tag);if(cls)e.className=cls;if(text!=null)e.textContent=text;return e}
function err(msg){var e=$('dash_error');e.textContent=msg;e.hidden=false;$('dash_sub').textContent=''}
function seg(b,n,total){var s=el('span','seg',n>0&&n/total>0.06?String(n):'');s.style.width=(100*n/total)+'%';s.style.background=COLORS[b];s.title=b+': '+n;return s}
function render(d){
  $('dash_title').textContent=(d.sprint?d.sprint+' ':'')+'Dashboard';
  $('dash_sub').textContent=d.total+' work items · '+d.resources.filter(function(r){return r.name!=='Unassigned'}).length+' resources';
  var k=$('kpis');k.innerHTML='';
  [[d.total,'Work items',''],[d.completion+'%','Complete','good'],[d.bucket_counts['In Progress']+d.bucket_counts.Testing,'In progress / testing',''],[d.open_bugs,'Open bugs','bad'],[d.backlog.total,'Backlog items',''],[d.unassigned,'Unassigned','warn']].forEach(function(t){var c=el('div','kpi '+t[2]);c.appendChild(el('b',null,t[0]));c.appendChild(el('span',null,t[1]));k.appendChild(c)});
  var sb=$('status_bar');sb.innerHTML='';ORDER.forEach(function(b){if(d.bucket_counts[b])sb.appendChild(seg(b,d.bucket_counts[b],d.total))});
  var lg=$('status_legend');lg.innerHTML='';ORDER.forEach(function(b){var li=el('li',null,b+' '+d.bucket_counts[b]);var dot=el('i');dot.style.background=COLORS[b];li.insertBefore(dot,li.firstChild);lg.appendChild(li)});
  var tb=$('type_bars');tb.innerHTML='';var max=Math.max.apply(null,Object.values(d.type_counts));
  Object.keys(d.type_counts).forEach(function(t){var r=el('div','hbar');r.appendChild(el('span','lab',t));var tr=el('div','track'),f=el('div','fill');f.style.width=(100*d.type_counts[t]/max)+'%';tr.appendChild(f);r.appendChild(tr);r.appendChild(el('span','num',d.type_counts[t]));tb.appendChild(r)});
  var rb=$('resource_bars');rb.innerHTML='';var rmax=Math.max.apply(null,d.resources.map(function(r){return r.total}));
  d.resources.forEach(function(r){var row=el('div','hbar');row.appendChild(el('span','lab',r.name));var tr=el('div','track stack');tr.style.width='100%';var inner=el('div','stack');inner.style.width=(100*r.total/rmax)+'%';ORDER.forEach(function(b){if(r[b])inner.appendChild(seg(b,r[b],r.total))});tr.appendChild(inner);row.appendChild(tr);row.appendChild(el('span','num',r.total+' · '+r.completion+'%'));rb.appendChild(row)});
  $('backlog_meta').textContent='· '+d.backlog.total+' items, '+d.backlog.unassigned+' unassigned, oldest '+d.backlog.oldest_days+' days (showing oldest 12)';
  var tbody=$('backlog_rows');tbody.innerHTML='';
  d.backlog.items.forEach(function(i){var tr=el('tr'),td=el('td');if(i.url&&/^https?:/.test(i.url)){var a=el('a',null,i.key);a.href=i.url;a.target='_blank';a.rel='noopener';td.appendChild(a)}else td.textContent=i.key;tr.appendChild(td);tr.appendChild(el('td',null,i.summary));tr.appendChild(el('td',null,i.type));tr.appendChild(el('td',i.owner==='Unassigned'?'bad':null,i.owner));tr.appendChild(el('td',null,i.age==null?'—':i.age+'d'));tbody.appendChild(tr)});
  $('dash_body').hidden=false;$('dash_error').hidden=true;
}
function run(name,text){
  var data=new FormData();data.append('csv_file',new File([text],name,{type:'text/csv'}));
  fetch('/api/summary',{method:'POST',body:data}).then(function(r){return r.json().then(function(o){if(!r.ok)throw new Error(o.error||'Could not read the CSV.');return o})}).then(function(d){if(!d.sprint){var m=/sprint[\s_-]*(\d+)/i.exec(name);if(m)d.sprint='Sprint '+m[1]}render(d)}).catch(function(e){err(e.message)});
}
function useFile(f){var r=new FileReader();r.onload=function(){try{sessionStorage.setItem(KEY,JSON.stringify({name:f.name,text:r.result}))}catch(e){}run(f.name,r.result)};r.readAsText(f)}
$('csv_file').addEventListener('change',function(e){if(e.target.files[0])useFile(e.target.files[0])});
var saved=null;try{saved=JSON.parse(sessionStorage.getItem(KEY)||'null')}catch(e){}
if(saved)run(saved.name,saved.text);
else fetch('/sample.csv').then(function(r){if(!r.ok)throw 0;return r.text()}).then(function(t){var n='Sprint_104_All_Work_Items.csv';try{sessionStorage.setItem(KEY,JSON.stringify({name:n,text:t}))}catch(e){}run(n,t)}).catch(function(){$('dash_sub').textContent='Load a Jira CSV export to see the dashboard.'});
})();
