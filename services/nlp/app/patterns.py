from __future__ import annotations
import csv
import pathlib
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List
REPORTING_THRESHOLD = 500000
STRUCTURING_BAND = 0.85
STRUCTURING_WINDOW_DAYS = 7
STRUCTURING_MIN_COUNT = 3
BURST_WINDOW_MINUTES = 60
BURST_MIN_CALLS = 4
NIGHT_START, NIGHT_END = (22, 5)
NIGHT_RATIO_THRESHOLD = 0.6
NIGHT_MIN_CALLS = 5
RAPID_PASSTHROUGH_DAYS = 3
PASSTHROUGH_RETENTION = 0.15

def _alert(kind, severity, title, detail, subjects, evidence) -> Dict[str, Any]:
    return {'id': f'ALERT-{kind}-{abs(hash((title, tuple(subjects)))) % 10000:04d}', 'kind': kind, 'severity': severity, 'title': title, 'detail': detail, 'subjects': subjects, 'evidence': evidence}

def detect_structuring(tx_path: pathlib.Path) -> List[Dict[str, Any]]:
    with tx_path.open(encoding='utf-8') as f:
        rows = list(csv.DictReader(f))
    by_pair = defaultdict(list)
    for r in rows:
        amt = float(r['amount_inr'])
        if REPORTING_THRESHOLD * STRUCTURING_BAND <= amt < REPORTING_THRESHOLD:
            by_pair[r['sender_name'], r['receiver_name']].append((datetime.strptime(r['date'], '%Y-%m-%d'), amt))
    alerts = []
    for (sender, receiver), items in by_pair.items():
        items.sort()
        for i in range(len(items)):
            window = [x for x in items if 0 <= (x[0] - items[i][0]).days <= STRUCTURING_WINDOW_DAYS]
            if len(window) >= STRUCTURING_MIN_COUNT:
                total = sum((a for _, a in window))
                amounts = ', '.join((f'Rs. {a:,.0f}' for _, a in window))
                alerts.append(_alert('STRUCTURING', 'HIGH', f'Possible structuring: {sender} to {receiver}', f'{len(window)} transfers totalling Rs. {total:,.0f} within {STRUCTURING_WINDOW_DAYS} days, each between Rs. {REPORTING_THRESHOLD * STRUCTURING_BAND:,.0f} and the Rs. {REPORTING_THRESHOLD:,.0f} reporting threshold.', [sender, receiver], [f'{d:%d/%m/%Y}: Rs. {a:,.0f}' for d, a in window]))
                break
    return alerts

def detect_passthrough(tx_path: pathlib.Path) -> List[Dict[str, Any]]:
    with tx_path.open(encoding='utf-8') as f:
        rows = list(csv.DictReader(f))
    inflow, outflow = (defaultdict(list), defaultdict(list))
    for r in rows:
        d = datetime.strptime(r['date'], '%Y-%m-%d')
        amt = float(r['amount_inr'])
        inflow[r['receiver_name']].append((d, amt, r['sender_name']))
        outflow[r['sender_name']].append((d, amt, r['receiver_name']))
    alerts = []
    for person, ins in inflow.items():
        outs = outflow.get(person, [])
        if not outs:
            continue
        matched = []
        for din, ain, src in ins:
            for dout, aout, dst in outs:
                if 0 <= (dout - din).days <= RAPID_PASSTHROUGH_DAYS:
                    matched.append((din, ain, src, dout, aout, dst))
        if not matched:
            continue
        total_in = sum({(m[0], m[1], m[2]): m[1] for m in matched}.values())
        total_out = sum({(m[3], m[4], m[5]): m[4] for m in matched}.values())
        if total_in and total_out / total_in >= 1 - PASSTHROUGH_RETENTION:
            alerts.append(_alert('PASSTHROUGH', 'HIGH', f'Funds pass-through: {person}', f'Rs. {total_in:,.0f} received and Rs. {total_out:,.0f} forwarded within {RAPID_PASSTHROUGH_DAYS} days, retaining under {int(PASSTHROUGH_RETENTION * 100)}%. Consistent with a layering conduit.', [person], [f'In Rs. {m[1]:,.0f} from {m[2]} on {m[0]:%d/%m/%Y}; out Rs. {m[4]:,.0f} to {m[5]} on {m[3]:%d/%m/%Y}' for m in matched[:4]]))
    return alerts

def detect_call_bursts(cdr_path: pathlib.Path, owners: Dict[str, str]) -> List[Dict[str, Any]]:
    with cdr_path.open(encoding='utf-8') as f:
        rows = list(csv.DictReader(f))
    by_pair = defaultdict(list)
    for r in rows:
        key = tuple(sorted([r['caller_msisdn'], r['callee_msisdn']]))
        by_pair[key].append((datetime.strptime(r['timestamp'], '%Y-%m-%d %H:%M:%S'), r['tower_location']))
    alerts = []
    for (a, b), times in by_pair.items():
        times.sort()
        for i, (t0, loc) in enumerate(times):
            window = [t for t, _ in times if 0 <= (t - t0).total_seconds() <= BURST_WINDOW_MINUTES * 60]
            if len(window) >= BURST_MIN_CALLS:
                na, nb = (owners.get(a, a), owners.get(b, b))
                alerts.append(_alert('CALL_BURST', 'MEDIUM', f'Call burst: {na} and {nb}', f'{len(window)} calls within {BURST_WINDOW_MINUTES} minutes on {t0:%d/%m/%Y}, first at {t0:%H:%M} near {loc}. Short-interval clustering is consistent with coordination around an event.', [na, nb], [f'{t:%d/%m/%Y %H:%M}' for t in window[:6]]))
                break
    return alerts

def detect_odd_hours(cdr_path: pathlib.Path, owners: Dict[str, str]) -> List[Dict[str, Any]]:
    with cdr_path.open(encoding='utf-8') as f:
        rows = list(csv.DictReader(f))
    stats = defaultdict(lambda: {'total': 0, 'night': 0})
    for r in rows:
        key = tuple(sorted([r['caller_msisdn'], r['callee_msisdn']]))
        h = datetime.strptime(r['timestamp'], '%Y-%m-%d %H:%M:%S').hour
        stats[key]['total'] += 1
        if h >= NIGHT_START or h <= NIGHT_END:
            stats[key]['night'] += 1
    alerts = []
    for (a, b), s in stats.items():
        if s['total'] >= NIGHT_MIN_CALLS and s['night'] / s['total'] >= NIGHT_RATIO_THRESHOLD:
            na, nb = (owners.get(a, a), owners.get(b, b))
            alerts.append(_alert('ODD_HOURS', 'LOW', f'Predominantly night-time contact: {na} and {nb}', f'{s['night']} of {s['total']} calls fall between {NIGHT_START}:00 and 0{NIGHT_END}:00.', [na, nb], [f'{s['night']}/{s['total']} calls in the {NIGHT_START}:00-0{NIGHT_END}:00 window']))
    return alerts

def detect_shared_identifiers(graph: Dict[str, Any]) -> List[Dict[str, Any]]:
    labels = {n['id']: n['label'] for n in graph['nodes']}
    types = {n['id']: n['type'] for n in graph['nodes']}
    users = defaultdict(set)
    for e in graph['edges']:
        if e['type'] in ('USES_PHONE', 'OWNS_ACCOUNT', 'OWNS_VEHICLE'):
            if types.get(e['source']) == 'PERSON':
                users[e['target']].add(labels[e['source']])
    alerts = []
    for ident, people in users.items():
        if len(people) >= 2:
            alerts.append(_alert('SHARED_IDENTIFIER', 'MEDIUM', f'Shared identifier: {labels.get(ident, ident)}', f'{types.get(ident)} {labels.get(ident)} is linked to {len(people)} individuals across sources. Shared handsets, accounts or vehicles frequently indicate an operational pool.', sorted(people), [f'linked to {p}' for p in sorted(people)]))
    return alerts

def detect_cross_cluster_bridge(graph: Dict[str, Any], analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
    mm = analysis.get('middleman')
    if not mm or mm['betweenness'] < 0.2:
        return []
    return [_alert('BRIDGE', 'HIGH', f'Single point of connection: {mm['label']}', f'Betweenness centrality {mm['betweenness']} — the highest in the network. This individual sits on the shortest path between two otherwise unconnected groups; removing them disconnects the network.', [mm['label']], [f'betweenness={mm['betweenness']}', f'degree={mm['degree']}'])]

def run_all(graph, analysis, cdr_path, tx_path, owners) -> List[Dict[str, Any]]:
    alerts = []
    alerts += detect_structuring(tx_path)
    alerts += detect_passthrough(tx_path)
    alerts += detect_call_bursts(cdr_path, owners)
    alerts += detect_odd_hours(cdr_path, owners)
    alerts += detect_shared_identifiers(graph)
    alerts += detect_cross_cluster_bridge(graph, analysis)
    order = {'HIGH': 0, 'MEDIUM': 1, 'LOW': 2}
    alerts.sort(key=lambda a: (order[a['severity']], a['title']))
    return alerts