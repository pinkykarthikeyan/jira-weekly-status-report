"""Shared data helpers for the resource-wise, backlog and dashboard views."""
import glob
import os
import re
from collections import Counter, OrderedDict, defaultdict
from datetime import date

from report_generator import col, filter_rows, norm, owner, parse_jira_date, read_jira_csv

BUCKETS = ['Done', 'Testing', 'In Progress', 'Open', 'Dropped']
DONE_STATUSES = {'done', 'closed', 'resolved', 'herdx accepted'}
DROPPED_STATUSES = {'discarded', 'rejected / not a bug', 'cannot reproduce', "won't do", 'duplicate'}
ALIASES = {'samuel kishore kumar': 'S. Kishore Kumar'}


def bucket(status):
    s = norm(status).lower()
    if s in DONE_STATUSES: return 'Done'
    if s in DROPPED_STATUSES: return 'Dropped'
    if 'progress' in s: return 'In Progress'
    if 'test' in s: return 'Testing'
    return 'Open'


def display_owner(value):
    name = norm(owner(value))
    if not name or name in ('—', '-') or name.lower() == 'unassigned':
        return 'Unassigned'
    return ALIASES.get(name.lower(), name)


def load_items(path, filters=None):
    headers, rows = read_jira_csv(path)
    rows = filter_rows(rows, headers, filters)
    c = {k: col(headers, v) for k, v in {
        'key': ['Issue key', 'Issue Key', 'Key'], 'summary': ['Summary', 'Title'],
        'type': ['Issue Type', 'Type'], 'owner': ['Assignee', 'Owner'], 'priority': ['Priority'],
        'status': ['Status'], 'created': ['Created'], 'updated': ['Updated'], 'url': ['URL']}.items()}
    get = lambda r, k: norm(r.get(c[k], '')) if c[k] else ''
    items = []
    for r in rows:
        status = get(r, 'status') or 'New / Open'
        items.append({
            'key': get(r, 'key'), 'summary': get(r, 'summary'), 'type': get(r, 'type') or 'Work Item',
            'owner': display_owner(r.get(c['owner'], '')) if c['owner'] else 'Unassigned',
            'priority': get(r, 'priority') or '—', 'status': status, 'bucket': bucket(status),
            'created': parse_jira_date(get(r, 'created')), 'updated': parse_jira_date(get(r, 'updated')),
            'url': get(r, 'url')})
    return items


def sprint_from_filename(name):
    m = re.search(r'sprint[\s_-]*(\d+)', name or '', re.I)
    return f'Sprint {m.group(1)}' if m else ''


def completion(items):
    active = [i for i in items if i['bucket'] != 'Dropped']
    return round(100 * sum(i['bucket'] == 'Done' for i in active) / len(active)) if active else 0


def by_resource(items):
    groups = defaultdict(list)
    for i in items: groups[i['owner']].append(i)
    names = sorted((n for n in groups if n != 'Unassigned'), key=lambda n: (-len(groups[n]), n.lower()))
    if 'Unassigned' in groups: names.append('Unassigned')
    return OrderedDict((n, groups[n]) for n in names)


def backlog_items(items):
    """Backlog = work that has not been picked up yet (status New / Open)."""
    return [i for i in items if i['bucket'] == 'Open']


def summary(items, sprint=''):
    res = by_resource(items)
    backlog = backlog_items(items)
    today = date.today()
    return {
        'sprint': sprint, 'total': len(items),
        'completion': completion(items),
        'bucket_counts': {b: sum(i['bucket'] == b for i in items) for b in BUCKETS},
        'status_counts': dict(Counter(i['status'] for i in items).most_common()),
        'type_counts': dict(Counter(i['type'] for i in items).most_common()),
        'open_bugs': sum(i['type'].lower() == 'bug' and i['bucket'] in ('Open', 'In Progress', 'Testing') for i in items),
        'unassigned': sum(i['owner'] == 'Unassigned' for i in items),
        'resources': [{'name': n, 'total': len(v), **{b: sum(i['bucket'] == b for i in v) for b in BUCKETS},
                       'completion': completion(v)} for n, v in res.items()],
        'backlog': {'total': len(backlog),
                    'by_type': dict(Counter(i['type'] for i in backlog).most_common()),
                    'unassigned': sum(i['owner'] == 'Unassigned' for i in backlog),
                    'oldest_days': max(((today - i['created']).days for i in backlog if i['created']), default=0),
                    'items': [{'key': i['key'], 'summary': i['summary'], 'type': i['type'], 'owner': i['owner'],
                               'url': i['url'], 'age': (today - i['created']).days if i['created'] else None}
                              for i in sorted(backlog, key=lambda i: i['created'] or today)[:12]]},
    }


def latest_sample(base):
    files = sorted(glob.glob(os.path.join(base, 'Sprint_*_All_Work_Items.csv')),
                   key=lambda p: [int(x) for x in re.findall(r'\d+', os.path.basename(p))])
    return files[-1] if files else None
