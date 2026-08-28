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
def col(headers,names):
    m={h.lower():h for h in headers}
    for n in names:
        if n.lower() in m:return m[n.lower()]
    for h in headers:
        if any(n.lower() in h.lower() for n in names):return h
    return None
def kind(s):
    x=norm(s).lower()
    return 'done' if any(a in x for a in ('done','closed','resolved')) else ('progress' if 'progress' in x else ('open' if 'open' in x or 'new' in x else 'other'))
def p(txt,size=6.2,lead=7.3,color=TEXT,bold=False,align=TA_LEFT):
    st=ParagraphStyle('x',fontName='Helvetica-Bold' if bold else 'Helvetica',fontSize=size,leading=lead,textColor=color,alignment=align,spaceAfter=0,spaceBefore=0)
    return Paragraph(escape(norm(txt)).replace('\n','<br/>'),st)
def owner(x):
    x=norm(x); return {'Samuel Ruthra Kumar':'Samuel Kishore Kumar','samuel ruthra kumar':'Samuel Kishore Kumar','Ajes Mini':'Alpa Mori','ajes mini':'Alpa Mori'}.get(x,x) or '—'
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
    c.saveState();c.setFont('Helvetica',7.5);c.setFillColor(NAVY);c.drawRightString(W-MR,6.5*mm,f'Page {d.page} of 2');c.restoreState()
def build_report(path,out,sprint='Sprint 100',week='Week of 17–21 Aug 2026'):
    with open(path,encoding='utf-8-sig',newline='') as f: rows=list(csv.DictReader(f))
    if not rows: raise ValueError('CSV contains no data')
    hs=list(rows[0]); tc=col(hs,['Issue Type','Type']); kc=col(hs,['Issue key','Issue Key','Key','Ticket']); sc=col(hs,['Summary','Title','Description']); stc=col(hs,['Status','Issue Status']); oc=col(hs,['Assignee','Owner','Assigned To']); lc=col(hs,['Issue Links','Issue Link','Linked Issues','Links','Parent'])
    issues={}
    for r in rows:
        k=norm(r.get(kc,'')) if kc else ''
        if not k: continue
        typ=norm(r.get(tc,'')).lower() if tc else ''
        issues[k]={'key':k,'summary':norm(r.get(sc,'')),'status':norm(r.get(stc,'')) or 'New / Open','owner':norm(r.get(oc,'')) if oc else '', 'kind':'bug' if 'bug' in typ else ('task' if 'task' in typ else 'story')}
    stories=[x for x in issues.values() if x['kind']=='story']
    tm=defaultdict(list); bm=defaultdict(list)
    for x in issues.values():
        if x['kind'] not in ('task','bug'):continue
        r=next((r for r in rows if norm(r.get(kc,''))==x['key']),{})
        blob=' '.join(norm(r.get(h,'')) for h in hs if ('link' in h.lower() or 'parent' in h.lower() or 'issue' in h.lower()))
        for ref in set(re.findall(r'\b[A-Z][A-Z0-9]+-\d+\b',blob)):
            if ref in issues and issues[ref]['kind']=='story': (bm if x['kind']=='bug' else tm)[ref].append(x)
    total=len(stories); ip=sum(kind(x['status'])=='progress' for x in stories); tasks=sum(len(v) for v in tm.values()); done=sum(kind(x['status'])=='done' for v in tm.values() for x in v); bugs=sum(1 for v in bm.values() for x in v if kind(x['status'])!='done'); prog=sum(1 for v in tm.values() for x in v if kind(x['status'])=='progress')
    title=ParagraphStyle('title',fontName='Helvetica-Bold',fontSize=18,leading=19,textColor=NAVY,alignment=TA_CENTER); sub=ParagraphStyle('sub',fontName='Helvetica-Bold',fontSize=9.2,leading=10.5,textColor=TEXT,alignment=TA_CENTER); sec=ParagraphStyle('sec',fontName='Helvetica-Bold',fontSize=9.2,leading=10.5,textColor=NAVY)
    doc=BaseDocTemplate(out,pagesize=A4,leftMargin=ML,rightMargin=MR,topMargin=MT,bottomMargin=MB)
    frame=Frame(ML,MB,CW,H-MT-MB,id='f',leftPadding=0,rightPadding=0,topPadding=0,bottomPadding=0);doc.addPageTemplates([PageTemplate(id='p',frames=[frame],onPage=page_no)])
    S=[Paragraph('WEEKLY STATUS REPORT',title),Spacer(1,1.2*mm),Paragraph(escape(f'{sprint}  |  {week}'),sub),Spacer(1,1.8*mm)]
    mw=CW/4
    cards=Table([[metric(str(total),'USER STORIES',NAVY,mw-3*mm),metric(str(ip),'IN PROGRESS',GREEN,mw-3*mm),metric(f'{done}/{tasks}','RELATED TASKS DONE',BLUE,mw-3*mm),metric(str(bugs),'OPEN RELATED BUGS',RED,mw-3*mm)]],colWidths=[mw]*4,style=TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),1.5*mm),('RIGHTPADDING',(0,0),(-1,-1),1.5*mm)]));S += [cards,Spacer(1,3*mm)]
    alert=Table([[p('!',16,18,WHITE,True,TA_CENTER),p(f'OVERALL STATUS: AT RISK\n{ip} of {total} user stories are in progress  |  {done}/{tasks} related tasks done  |  {bugs} related bugs are open and require closure/verification.',7.4,8.7,RED,True)]],colWidths=[15*mm,CW-15*mm],rowHeights=[15*mm],style=TableStyle([('BACKGROUND',(0,0),(0,0),RED),('BACKGROUND',(1,0),(1,0),PALE_RED),('BOX',(0,0),(-1,-1),.55,RED),('VALIGN',(0,0),(-1,-1),'MIDDLE'),('LEFTPADDING',(0,0),(-1,-1),2*mm),('RIGHTPADDING',(0,0),(-1,-1),2*mm)]));S += [alert,Spacer(1,3*mm)]
    boxes=Table([[insight('KEY HIGHLIGHTS',[f'{ip} of {total} user stories are in progress.',f'{done} of {tasks} related tasks are completed.' if tasks else 'No related tasks in export.',f'{bugs} related bugs remain open.',f'{prog} related task remains in progress.' if prog==1 else f'{prog} related tasks remain in progress.','Several in-progress stories have no linked tasks/bugs in the export.'],'◎',CW/3-2*mm),insight('NEXT FOCUS',['Close the remaining related task.' if tasks-done==1 else f'Close the remaining {tasks-done} related tasks.',f'Resolve and verify the {bugs} open bugs under Activity Log.' if bugs else 'Continue QA verification.','Update story status after QA and validation.'],'↗',CW/3-2*mm),insight('MANAGEMENT ATTENTION',['Review new/open stories where associated tasks are already done.','Track the Activity Log Tab/Web and mobile stories closely.','Ensure Jira story status reflects actual delivery readiness.'],'●',CW/3-2*mm)]],colWidths=[CW/3]*3,style=TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),1.2*mm),('RIGHTPADDING',(0,0),(-1,-1),1.2*mm)]));S += [boxes,Spacer(1,3.5*mm),Paragraph('▮  SPRINT 100 – USER STORY SNAPSHOT (ALL 20 STORIES)',sec),Spacer(1,1.2*mm)]
    widths=[6*mm,72*mm,22*mm,24*mm,22*mm,22*mm,CW-168*mm]; data=[[p('#',7,8,WHITE,True,TA_CENTER),p('USER STORY / WORKSTREAM',7,8,WHITE,True,TA_CENTER),p('STATUS',7,8,WHITE,True,TA_CENTER),p('TASK STATUS',7,8,WHITE,True,TA_CENTER),p('BUG STATUS',7,8,WHITE,True,TA_CENTER),p('OWNER',7,8,WHITE,True,TA_CENTER),p('NOTES',7,8,WHITE,True,TA_CENTER)]]
    for i,s in enumerate(stories,1):
        ts=tm.get(s['key'],[]); bs=bm.get(s['key'],[]); td=sum(kind(x['status'])=='done' for x in ts); tp=sum(kind(x['status'])=='progress' for x in ts); ttxt='—' if not ts else (f'{td} / {len(ts)} Done' if not tp else f'{td} / {len(ts)} Done + {tp} In Progress'); bo=sum(kind(x['status'])!='done' for x in bs); btxt='—' if not bs else f'{bo} Open' if bo else '0 Open'; note=f'{bo} open bug'+('s' if bo!=1 else '') if bo else (f'{tp} task'+('s' if tp!=1 else '')+' in progress' if tp else ('No linked items' if not ts else 'All tasks done'))
        data.append([p(str(i),5.1,5.8,TEXT,True,TA_CENTER),p(f"{s['key']} – {s['summary']}",5.1,5.8),scell(s['status'],24*mm),scell(ttxt,28*mm),scell(btxt,27*mm),p(owner(s['owner']),5.1,5.8,TEXT,True),p(note,5.1,5.8)])
    tab=Table(data,colWidths=widths,repeatRows=1,style=TableStyle([('BACKGROUND',(0,0),(-1,0),NAVY),('GRID',(0,0),(-1,-1),.35,GRID),('VALIGN',(0,0),(-1,-1),'MIDDLE'),('LEFTPADDING',(0,0),(-1,-1),1.3*mm),('RIGHTPADDING',(0,0),(-1,-1),1.3*mm),('TOPPADDING',(0,1),(-1,-1),.65*mm),('BOTTOMPADDING',(0,1),(-1,-1),.65*mm)]))
    for r in range(2,len(data)+1):
        if r%2==0: tab.setStyle(TableStyle([('BACKGROUND',(0,r-1),(-1,r-1),colors.HexColor('#FAFBFC'))]))
    S += [tab,PageBreak(),Paragraph('▮  DETAILED DELIVERY STATUS (User Story → Tasks / Bugs)',sec),Spacer(1,1.5*mm)]
    dw=[6*mm,68*mm,CW-74*mm]; dd=[[p('#',6.5,7,WHITE,True,TA_CENTER),p('USER STORY / WORKSTREAM',6.5,7,WHITE,True,TA_CENTER),p('LINKED TASKS / BUGS — CURRENT STATUS',6.5,7,WHITE,True,TA_CENTER)]]
    for i,s in enumerate(stories,1):
        links=tm.get(s['key'],[])+bm.get(s['key'],[]); txt='No linked tasks / bugs in Jira export' if not links else '\n'.join(f"{x['key']} — {'Bug' if x['kind']=='bug' else 'Task'} — {x['summary']} — {x['status']}" for x in links); dd.append([p(str(i),6,7,TEXT,True,TA_CENTER),p(f"{s['key']} – {s['summary']}",6,7,NAVY),p(txt,5.5,6.5,MUTED if not links else TEXT)])
    dt=Table(dd,colWidths=dw,repeatRows=1,style=TableStyle([('BACKGROUND',(0,0),(-1,0),NAVY),('GRID',(0,0),(-1,-1),.3,GRID),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),1.4*mm),('RIGHTPADDING',(0,0),(-1,-1),1.4*mm),('TOPPADDING',(0,1),(-1,-1),1*mm),('BOTTOMPADDING',(0,1),(-1,-1),1*mm)]));S += [dt];doc.build(S)
