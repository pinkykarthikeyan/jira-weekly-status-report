import csv,re
from collections import defaultdict
from xml.sax.saxutils import escape
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER,TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import BaseDocTemplate,PageTemplate,Frame,Paragraph,Spacer,Table,TableStyle,PageBreak
NAVY=colors.HexColor('#123A78'); GREEN=colors.HexColor('#0A963F'); BLUE=colors.HexColor('#1767C5'); RED=colors.HexColor('#E21B23'); TEXT=colors.HexColor('#14213D'); MUTED=colors.HexColor('#5C6675'); GRID=colors.HexColor('#C9D2DD'); PALE_BLUE=colors.HexColor('#EAF2FD'); PALE_GREEN=colors.HexColor('#EAF7EF'); PALE_RED=colors.HexColor('#FFF0F1'); PALE_GRAY=colors.HexColor('#F4F6F8'); ORANGE=colors.HexColor('#C97A00'); WHITE=colors.white
W,H=A4; ML=8*mm; MR=8*mm; MT=7*mm; MB=7*mm; CW=W-ML-MR

def norm(x): return re.sub(r'\s+',' ',str(x or '')).strip()
PRODUCTION_LABELS={'prod','firebase'}

def read_jira_csv(path):
    with open(path,encoding='utf-8-sig',newline='') as f:
        reader=csv.reader(f)
        headers=next(reader,[])
        rows=[]
        for values in reader:
            row={}
            for i,h in enumerate(headers):
                value=norm(values[i] if i < len(values) else '')
                if h in row and value:
                    row[h]=f'{row[h]}; {value}' if row[h] else value
                elif h not in row:
                    row[h]=value
            rows.append(row)
    if not rows: raise ValueError('CSV contains no data')
    return headers,rows

def labels_for(row,headers):
    labels=[]
    for header in headers:
        if header.strip().lower() != 'labels': continue
        labels.extend(part.strip().lower() for part in re.split(r'[;,]',row.get(header,'')) if part.strip())
    return set(labels)

def col(headers,names):
    m={h.lower():h for h in headers}
    for n in names:
        if n.lower() in m:return m[n.lower()]
    for h in headers:
        if any(n.lower() in h.lower() for n in names):return h
    return None

def split_values(value):
    return [norm(part) for part in re.split(r';',str(value or '')) if norm(part)]

def get_filter_options(path):
    headers,rows=read_jira_csv(path)
    label_values=set()
    for row in rows:
        label_values.update(labels_for(row,headers))
    sprint_col=col(headers,['Sprint'])
    status_col=col(headers,['Status','Issue Status'])
    type_col=col(headers,['Issue Type','Type'])
    return {
        'labels':sorted(label_values),
        'sprints':sorted({value for row in rows for value in split_values(row.get(sprint_col,''))}) if sprint_col else [],
        'statuses':sorted({norm(row.get(status_col,'')) for row in rows if norm(row.get(status_col,''))}) if status_col else [],
        'workitem_types':sorted({norm(row.get(type_col,'')) for row in rows if norm(row.get(type_col,''))}) if type_col else [],
    }

def filter_rows(rows,headers,filters):
    filters=filters or {}
    selected_label=norm(filters.get('label','')).lower()
    selected_sprint=norm(filters.get('sprint','')).lower()
    selected_status=norm(filters.get('status','')).lower()
    selected_type=norm(filters.get('workitem_type','')).lower()
    sprint_col=col(headers,['Sprint'])
    status_col=col(headers,['Status','Issue Status'])
    type_col=col(headers,['Issue Type','Type'])
    filtered=[]
    for row in rows:
        if selected_label and selected_label not in labels_for(row,headers): continue
        if selected_sprint and selected_sprint not in {value.lower() for value in split_values(row.get(sprint_col,''))}: continue
        if selected_status and norm(row.get(status_col,'')).lower() != selected_status: continue
        if selected_type and norm(row.get(type_col,'')).lower() != selected_type: continue
        filtered.append(row)
    return filtered

def kind(s):
    x=norm(s).lower()
    return 'done' if any(a in x for a in ('done','closed','resolved')) else ('progress' if 'progress' in x else ('open' if 'open' in x or 'new' in x else 'other'))
def p(txt,size=6.2,lead=7.3,color=TEXT,bold=False,align=TA_LEFT):
    st=ParagraphStyle('x',fontName='Helvetica-Bold' if bold else 'Helvetica',fontSize=size,leading=lead,textColor=color,alignment=align,spaceAfter=0,spaceBefore=0)
    return Paragraph(escape(norm(txt)).replace('\n','<br/>'),st)
def owner(x):
    x=norm(x); return {'Samuel Ruthra Kumar':'Samuel Kishore Kumar','samuel ruthra kumar':'Samuel Kishore Kumar','Ajes Mini':'Alpa Mori','ajes mini':'Alpa Mori'}.get(x,x) or '—'
def is_production_ticket(row,headers):
    """Include tickets carrying the exact Jira label ``prod`` or ``firebase``."""
    return bool(labels_for(row,headers) & PRODUCTION_LABELS)
def scell(text,w=28*mm):
    k=kind(text); bg,fg=(PALE_GREEN,GREEN) if k=='done' else ((colors.HexColor('#FFF3D6'),ORANGE) if k=='progress' else ((PALE_BLUE,BLUE) if k=='open' else (PALE_GRAY,TEXT)))
    return Table([[p(text,5.2,5.8,fg,True,TA_CENTER)]],colWidths=[w],rowHeights=[6.3*mm],style=TableStyle([('BACKGROUND',(0,0),(-1,-1),bg),('VALIGN',(0,0),(-1,-1),'MIDDLE'),('LEFTPADDING',(0,0),(-1,-1),1),('RIGHTPADDING',(0,0),(-1,-1),1),('TOPPADDING',(0,0),(-1,-1),0),('BOTTOMPADDING',(0,0),(-1,-1),0)]))
def metric(num,label,color,w):
    a=Table([[p(num,17,18,WHITE,True,TA_CENTER)]],colWidths=[w],rowHeights=[12*mm],style=TableStyle([('BACKGROUND',(0,0),(-1,-1),color),('VALIGN',(0,0),(-1,-1),'MIDDLE'),('LEFTPADDING',(0,0),(-1,-1),2),('RIGHTPADDING',(0,0),(-1,-1),2)]))
    b=Table([[p(label,7.2,8.2,NAVY,True,TA_CENTER)]],colWidths=[w],rowHeights=[8*mm],style=TableStyle([('BACKGROUND',(0,0),(-1,-1),WHITE),('BOX',(0,0),(-1,-1),.55,color),('VALIGN',(0,0),(-1,-1),'MIDDLE')]))
    return Table([[a],[b]],colWidths=[w],rowHeights=[15*mm,9*mm],style=TableStyle([('LEFTPADDING',(0,0),(-1,-1),0),('RIGHTPADDING',(0,0),(-1,-1),0),('TOPPADDING',(0,0),(-1,-1),0),('BOTTOMPADDING',(0,0),(-1,-1),0)]))
def insight(title,bullets,icon,w):
    head=Table([[p(icon,9,10,NAVY,True,TA_CENTER),p(title,8.7,9.7,NAVY,True)]],colWidths=[9*mm,w-9*mm],rowHeights=[8*mm],style=TableStyle([('BACKGROUND',(0,0),(-1,-1),PALE_GRAY),('VALIGN',(0,0),(-1,-1),'MIDDLE'),('LEFTPADDING',(0,0),(-1,-1),0),('RIGHTPADDING',(0,0),(-1,-1),0)]))
    data=[[head]]+[[p('• '+b,7.1,9,TEXT)] for b in bullets]
    return Table(data,colWidths=[w],style=TableStyle([('BOX',(0,0),(-1,-1),.55,GRID),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),3*mm),('RIGHTPADDING',(0,0),(-1,-1),3*mm),('TOPPADDING',(0,0),(-1,0),1.3*mm),('BOTTOMPADDING',(0,0),(-1,0),1.3*mm),('TOPPADDING',(0,1),(-1,-1),.5*mm),('BOTTOMPADDING',(0,1),(-1,-1),.4*mm)]))
def page_no(c,d):
    c.saveState();c.setFont('Helvetica',7.5);c.setFillColor(NAVY);c.drawRightString(W-MR,6.5*mm,f'Page {d.page}');c.restoreState()

def build_production_pdf(out,production_tickets,sprint,week):
    title=ParagraphStyle('production_title',fontName='Helvetica-Bold',fontSize=18,leading=19,textColor=NAVY,alignment=TA_CENTER)
    sub=ParagraphStyle('production_sub',fontName='Helvetica-Bold',fontSize=9.2,leading=10.5,textColor=TEXT,alignment=TA_CENTER)
    sec=ParagraphStyle('production_sec',fontName='Helvetica-Bold',fontSize=9.2,leading=10.5,textColor=NAVY)
    doc=BaseDocTemplate(out,pagesize=A4,leftMargin=ML,rightMargin=MR,topMargin=MT,bottomMargin=MB)
    frame=Frame(ML,MB,CW,H-MT-MB,id='production',leftPadding=0,rightPadding=0,topPadding=0,bottomPadding=0)
    doc.addPageTemplates([PageTemplate(id='production',frames=[frame],onPage=page_no)])
    production_total=len(production_tickets)
    production_done=sum(kind(x['status'])=='done' for x in production_tickets)
    production_progress=sum(kind(x['status'])=='progress' for x in production_tickets)
    production_open=production_total-production_done
    S=[Paragraph('PRODUCTION TICKET REPORT',title),Spacer(1,1.2*mm),Paragraph(escape(f'{sprint}  |  {week}  |  Labels: prod or firebase'),sub),Spacer(1,1.8*mm)]
    pmw=CW/4
    production_cards=Table([[metric(str(production_total),'PRODUCTION TICKETS',NAVY,pmw-3*mm),metric(str(production_progress),'IN PROGRESS',GREEN,pmw-3*mm),metric(str(production_done),'COMPLETED',BLUE,pmw-3*mm),metric(str(production_open),'OPEN / PENDING',RED,pmw-3*mm)]],colWidths=[pmw]*4,style=TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),1.5*mm),('RIGHTPADDING',(0,0),(-1,-1),1.5*mm)]))
    S += [production_cards,Spacer(1,3*mm)]
    production_message = ('No tickets with the prod or firebase label were identified in this Jira export.' if not production_tickets else f'{production_open} production ticket'+(' remains' if production_open==1 else 's remain')+' open or pending review.')
    production_color=GREEN if not production_open else RED
    production_bg=PALE_GREEN if not production_open else PALE_RED
    production_alert=Table([[p('!',16,18,WHITE,True,TA_CENTER),p(f'PRODUCTION STATUS: {"CLEAR" if not production_open else "AT RISK"}\n{production_message}',7.4,8.7,production_color,True)]],colWidths=[15*mm,CW-15*mm],rowHeights=[15*mm],style=TableStyle([('BACKGROUND',(0,0),(0,0),production_color),('BACKGROUND',(1,0),(1,0),production_bg),('BOX',(0,0),(-1,-1),.55,production_color),('VALIGN',(0,0),(-1,-1),'MIDDLE'),('LEFTPADDING',(0,0),(-1,-1),2*mm),('RIGHTPADDING',(0,0),(-1,-1),2*mm)]))
    S += [production_alert,Spacer(1,3.5*mm),Paragraph('▮  PRODUCTION TICKETS — CURRENT STATUS',sec),Spacer(1,1.2*mm)]
    pw=[6*mm,29*mm,18*mm,25*mm,29*mm,CW-107*mm]
    pd=[[p('#',7,8,WHITE,True,TA_CENTER),p('TICKET',7,8,WHITE,True,TA_CENTER),p('TYPE',7,8,WHITE,True,TA_CENTER),p('STATUS',7,8,WHITE,True,TA_CENTER),p('OWNER',7,8,WHITE,True,TA_CENTER),p('SUMMARY / NOTES',7,8,WHITE,True,TA_CENTER)]]
    if production_tickets:
        for i,x in enumerate(production_tickets,1):
            pd.append([p(str(i),5.5,6.2,TEXT,True,TA_CENTER),p(x['key'],5.5,6.2,NAVY,True,TA_CENTER),p(x['type'],5.2,6),scell(x['status'],25*mm),p(owner(x['owner']),5.2,6,TEXT,True),p(x['summary'] or 'No summary provided',5.2,6.1)])
    else:
        pd.append([p('—',6,7,TEXT,True,TA_CENTER),p('No production tickets found',6,7,MUTED),p('—',6,7,MUTED),p('—',6,7,MUTED),p('—',6,7,MUTED),p('Add the prod or firebase label in Jira to include a ticket here.',6,7,MUTED)])
    pt=Table(pd,colWidths=pw,repeatRows=1,style=TableStyle([('BACKGROUND',(0,0),(-1,0),NAVY),('GRID',(0,0),(-1,-1),.35,GRID),('VALIGN',(0,0),(-1,-1),'MIDDLE'),('LEFTPADDING',(0,0),(-1,-1),1.3*mm),('RIGHTPADDING',(0,0),(-1,-1),1.3*mm),('TOPPADDING',(0,1),(-1,-1),1*mm),('BOTTOMPADDING',(0,1),(-1,-1),1*mm)]))
    for r in range(2,len(pd)+1):
        if r%2==0: pt.setStyle(TableStyle([('BACKGROUND',(0,r-1),(-1,r-1),colors.HexColor('#FAFBFC'))]))
    S += [pt]
    doc.build(S)

def build_report(path,out,sprint='Sprint 101',week='Week of 17–21 Aug 2026',report_kind='backlog',filters=None):
    hs,rows=read_jira_csv(path)
    rows=filter_rows(rows,hs,filters)
    tc=col(hs,['Issue Type','Type']); kc=col(hs,['Issue key','Issue Key','Key','Ticket']); sc=col(hs,['Summary','Title','Description']); stc=col(hs,['Status','Issue Status']); oc=col(hs,['Assignee','Owner','Assigned To']); lc=col(hs,['Issue Links','Issue Link','Linked Issues','Links','Parent'])
    issues={}
    for r in rows:
        k=norm(r.get(kc,'')) if kc else ''
        if not k: continue
        typ=norm(r.get(tc,'')).lower() if tc else ''
        issues[k]={'key':k,'summary':norm(r.get(sc,'')),'status':norm(r.get(stc,'')) or 'New / Open','owner':norm(r.get(oc,'')) if oc else '', 'kind':'bug' if 'bug' in typ else ('task' if 'task' in typ else 'story')}
    production_tickets=[]
    for r in rows:
        k=norm(r.get(kc,'')) if kc else ''
        if not k or not is_production_ticket(r,hs): continue
        typ=norm(r.get(tc,'')) if tc else 'Ticket'
        production_tickets.append({'key':k,'summary':norm(r.get(sc,'')),'status':norm(r.get(stc,'')) or 'New / Open','owner':norm(r.get(oc,'')) if oc else '', 'type':typ})
    if report_kind == 'production':
        build_production_pdf(out,production_tickets,sprint,week)
        return
    production_keys={x['key'] for x in production_tickets}
    issues={k:x for k,x in issues.items() if k not in production_keys}
    stories=[x for x in issues.values() if x['kind']=='story']
    tm=defaultdict(list); bm=defaultdict(list)
    for x in issues.values():
        if x['kind'] not in ('task','bug'):continue
        r=next((r for r in rows if norm(r.get(kc,''))==x['key']),{})
        blob=' '.join(norm(r.get(h,'')) for h in hs if ('link' in h.lower() or 'parent' in h.lower() or 'issue' in h.lower()))
        for ref in set(re.findall(r'\b[A-Z][A-Z0-9]+-\d+\b',blob)):
            if ref in issues and issues[ref]['kind']=='story': (bm if x['kind']=='bug' else tm)[ref].append(x)
    # Support both Story-based exports and Task/Bug-only exports.
    tasks_list = [x for x in issues.values() if x['kind'] == 'task']
    bugs_list = [x for x in issues.values() if x['kind'] == 'bug']

    if stories:
        total = len(stories)
        ip = sum(kind(x['status']) == 'progress' for x in stories)
        tasks = sum(len(v) for v in tm.values())
        done = sum(kind(x['status']) == 'done' for v in tm.values() for x in v)
        bugs = sum(1 for v in bm.values() for x in v if kind(x['status']) != 'done')
        prog = sum(1 for v in tm.values() for x in v if kind(x['status']) == 'progress')
        report_items = stories
        snapshot_label = 'USER STORY'
    else:
        report_items = tasks_list + bugs_list
        total = len(report_items)
        ip = sum(kind(x['status']) == 'progress' for x in report_items)
        tasks = len(tasks_list)
        done = sum(kind(x['status']) == 'done' for x in tasks_list)
        bugs = sum(kind(x['status']) != 'done' for x in bugs_list)
        prog = sum(kind(x['status']) == 'progress' for x in tasks_list)
        snapshot_label = 'WORK ITEM'
    title=ParagraphStyle('title',fontName='Helvetica-Bold',fontSize=18,leading=19,textColor=NAVY,alignment=TA_CENTER); sub=ParagraphStyle('sub',fontName='Helvetica-Bold',fontSize=9.2,leading=10.5,textColor=TEXT,alignment=TA_CENTER); sec=ParagraphStyle('sec',fontName='Helvetica-Bold',fontSize=9.2,leading=10.5,textColor=NAVY)
    doc=BaseDocTemplate(out,pagesize=A4,leftMargin=ML,rightMargin=MR,topMargin=MT,bottomMargin=MB)
    frame=Frame(ML,MB,CW,H-MT-MB,id='f',leftPadding=0,rightPadding=0,topPadding=0,bottomPadding=0);doc.addPageTemplates([PageTemplate(id='p',frames=[frame],onPage=page_no)])
    S=[Paragraph('WEEKLY STATUS REPORT',title),Spacer(1,1.2*mm),Paragraph(escape(f'{sprint}  |  {week}'),sub),Spacer(1,1.8*mm)]
    mw=CW/4
    cards=Table([[metric(str(total),'USER STORIES',NAVY,mw-3*mm),metric(str(ip),'IN PROGRESS',GREEN,mw-3*mm),metric(f'{done}/{tasks}','RELATED TASKS DONE',BLUE,mw-3*mm),metric(str(bugs),'OPEN RELATED BUGS',RED,mw-3*mm)]],colWidths=[mw]*4,style=TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),1.5*mm),('RIGHTPADDING',(0,0),(-1,-1),1.5*mm)]));S += [cards,Spacer(1,3*mm)]
    item_word = 'user stories' if stories else 'work items'
    task_word = 'related tasks' if stories else 'tasks'
    bug_word = 'related bugs' if stories else 'bugs'
    alert_status = 'AT RISK' if total else 'NO GENERAL WORK ITEMS'
    alert_text = (f'{ip} of {total} {item_word} are in progress  |  {done}/{tasks} {task_word} done  |  {bugs} {bug_word} are open and require closure/verification.'
                  if total else 'No non-production work items were identified in this Jira export. See the separate production ticket report.')
    alert_color = RED if total else BLUE
    alert_bg = PALE_RED if total else PALE_BLUE
    alert=Table([[p('!',16,18,WHITE,True,TA_CENTER),p(f'OVERALL STATUS: {alert_status}\n{alert_text}',7.4,8.7,alert_color,True)]],colWidths=[15*mm,CW-15*mm],rowHeights=[15*mm],style=TableStyle([('BACKGROUND',(0,0),(0,0),alert_color),('BACKGROUND',(1,0),(1,0),alert_bg),('BOX',(0,0),(-1,-1),.55,alert_color),('VALIGN',(0,0),(-1,-1),'MIDDLE'),('LEFTPADDING',(0,0),(-1,-1),2*mm),('RIGHTPADDING',(0,0),(-1,-1),2*mm)]));S += [alert,Spacer(1,3*mm)]
    highlights = [
        f'{ip} of {total} {item_word} are in progress.',
        f'{done} of {tasks} {task_word} are completed.' if tasks else 'No tasks in export.',
        f'{bugs} {bug_word} remain open.',
        f'{prog} task remains in progress.' if prog == 1 else f'{prog} tasks remain in progress.'
    ]
    if stories:
        highlights.append('Several in-progress stories have no linked tasks/bugs in the export.')
    else:
        highlights.append('Metrics are calculated directly from the exported tasks and bugs.')

    remaining_tasks = max(tasks - done, 0)
    next_focus = []
    if remaining_tasks:
        next_focus.append('Close the remaining task.' if remaining_tasks == 1 else f'Close the remaining {remaining_tasks} tasks.')
    next_focus.extend([
        f'Resolve and verify the {bugs} open bugs.' if bugs else 'Continue QA verification.',
        'Update Jira status after QA and validation.'
    ])

    attention = (
        ['Review new/open stories where associated tasks are already done.',
         'Track high-priority stories closely.',
         'Ensure Jira story status reflects actual delivery readiness.']
        if stories else
        ['Review any remaining non-completed work items.',
         'Verify open bugs and acceptance status.',
         'Ensure Jira status reflects actual delivery readiness.']
    )

    boxes=Table([[insight('KEY HIGHLIGHTS',highlights,'◎',CW/3-2*mm),insight('NEXT FOCUS',next_focus,'↗',CW/3-2*mm),insight('MANAGEMENT ATTENTION',attention,'●',CW/3-2*mm)]],colWidths=[CW/3]*3,style=TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),1.2*mm),('RIGHTPADDING',(0,0),(-1,-1),1.2*mm)]))
    snapshot_title = f'▮  {sprint.upper()} – {snapshot_label} SNAPSHOT (ALL {total} {"STORIES" if stories else "ITEMS"})'
    S += [boxes,Spacer(1,3.5*mm),Paragraph(snapshot_title,sec),Spacer(1,1.2*mm)]
    status_width=22*mm; task_width=24*mm; bug_width=22*mm
    widths=[6*mm,72*mm,status_width,task_width,bug_width,22*mm,CW-168*mm]; data=[[p('#',7,8,WHITE,True,TA_CENTER),p('USER STORY / WORKSTREAM',7,8,WHITE,True,TA_CENTER),p('STATUS',7,8,WHITE,True,TA_CENTER),p('TASK STATUS',7,8,WHITE,True,TA_CENTER),p('BUG STATUS',7,8,WHITE,True,TA_CENTER),p('OWNER',7,8,WHITE,True,TA_CENTER),p('NOTES',7,8,WHITE,True,TA_CENTER)]]
    for i,s in enumerate(report_items,1):
        if stories:
            ts=tm.get(s['key'],[]); bs=bm.get(s['key'],[]); td=sum(kind(x['status'])=='done' for x in ts); tp=sum(kind(x['status'])=='progress' for x in ts); ttxt='—' if not ts else (f'{td} / {len(ts)} Done' if not tp else f'{td} / {len(ts)} Done + {tp} In Progress'); bo=sum(kind(x['status'])!='done' for x in bs); btxt='—' if not bs else f'{bo} Open' if bo else '0 Open'; note=f'{bo} open bug'+('s' if bo!=1 else '') if bo else (f'{tp} task'+('s' if tp!=1 else '')+' in progress' if tp else ('No linked items' if not ts else 'All tasks done'))
        else:
            ttxt = s['status'] if s['kind'] == 'task' else '—'
            btxt = s['status'] if s['kind'] == 'bug' else '—'
            note = 'Task' if s['kind'] == 'task' else 'Bug'
        data.append([p(str(i),5.1,5.8,TEXT,True,TA_CENTER),p(f"{s['key']} – {s['summary']}",5.1,5.8),scell(s['status'],status_width),scell(ttxt,task_width),scell(btxt,bug_width),p(owner(s['owner']),5.1,5.8,TEXT,True),p(note,5.1,5.8)])
    tab=Table(data,colWidths=widths,repeatRows=1,style=TableStyle([('BACKGROUND',(0,0),(-1,0),NAVY),('GRID',(0,0),(-1,-1),.35,GRID),('VALIGN',(0,0),(-1,-1),'MIDDLE'),('LEFTPADDING',(0,0),(-1,-1),1.3*mm),('RIGHTPADDING',(0,0),(-1,-1),1.3*mm),('TOPPADDING',(0,1),(-1,-1),.65*mm),('BOTTOMPADDING',(0,1),(-1,-1),.65*mm)]))
    for r in range(2,len(data)+1):
        if r%2==0: tab.setStyle(TableStyle([('BACKGROUND',(0,r-1),(-1,r-1),colors.HexColor('#FAFBFC'))]))
    detailed_title = '▮  DETAILED DELIVERY STATUS (User Story → Tasks / Bugs)' if stories else '▮  DETAILED DELIVERY STATUS (All Exported Work Items)'
    S += [tab,PageBreak(),Paragraph(detailed_title,sec),Spacer(1,1.5*mm)]
    dw=[6*mm,68*mm,CW-74*mm]; dd=[[p('#',6.5,7,WHITE,True,TA_CENTER),p('USER STORY / WORKSTREAM',6.5,7,WHITE,True,TA_CENTER),p('LINKED TASKS / BUGS — CURRENT STATUS',6.5,7,WHITE,True,TA_CENTER)]]
    for i,s in enumerate(report_items,1):
        if stories:
            links=tm.get(s['key'],[])+bm.get(s['key'],[])
            txt='No linked tasks / bugs in Jira export' if not links else '\n'.join(f"{x['key']} — {'Bug' if x['kind']=='bug' else 'Task'} — {x['summary']} — {x['status']}" for x in links)
            txt_color = MUTED if not links else TEXT
        else:
            txt=f"{'Bug' if s['kind']=='bug' else 'Task'} — Current Status: {s['status']}"
            txt_color = TEXT
        dd.append([p(str(i),6,7,TEXT,True,TA_CENTER),p(f"{s['key']} – {s['summary']}",6,7,NAVY),p(txt,5.5,6.5,txt_color)])
    dt=Table(dd,colWidths=dw,repeatRows=1,style=TableStyle([('BACKGROUND',(0,0),(-1,0),NAVY),('GRID',(0,0),(-1,-1),.3,GRID),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),1.4*mm),('RIGHTPADDING',(0,0),(-1,-1),1.4*mm),('TOPPADDING',(0,1),(-1,-1),1*mm),('BOTTOMPADDING',(0,1),(-1,-1),1*mm)]))
    S += [dt]
    doc.build(S)

def build_reports(path,backlog_out,production_out,sprint='Sprint 101',week='Week of 17–21 Aug 2026',filters=None):
    """Generate the two stakeholder reports from one Jira export."""
    build_report(path,backlog_out,sprint,week,report_kind='backlog',filters=filters)
    build_report(path,production_out,sprint,week,report_kind='production',filters=filters)
