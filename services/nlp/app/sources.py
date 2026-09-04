from __future__ import annotations
import csv
import pathlib
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List
PIPELINE_VERSION = '0.3.0'
PHONE_OWNERS: Dict[str, str] = {'+919830011122': 'Vikram Singh', '+919830012345': 'Imran Sheikh', '+919007654321': 'Bablu Mondal', '+919123456780': 'Sohail Ansari', '+919845001122': 'Rakesh Yadav', '+919845002233': 'Pappu Das', '+919845003344': 'Kallu Halder', '+919845004455': 'Amit Agarwal'}

def _norm_msisdn(v: str) -> str:
    digits = ''.join((c for c in v if c.isdigit()))
    return '+91' + digits[-10:]

def _mk(entity_id: str, etype: str, value: str, normalized: str | None=None, conf: float=0.99) -> Dict[str, Any]:
    return {'entity_id': entity_id, 'type': etype, 'value': value, 'normalized': normalized or value, 'canonical_value': value, 'confidence': conf, 'extractor': 'structured', 'spans': [], 'aliases': [], 'cluster_id': f's_{etype}_{normalized or value}'}

def parse_cdr(path: pathlib.Path, doc_id: str='CDR-2026-Q1') -> Dict[str, Any]:
    rows: List[Dict[str, str]] = []
    with path.open(encoding='utf-8') as f:
        rows = list(csv.DictReader(f))
    pairs: Dict[tuple, Dict[str, Any]] = defaultdict(lambda: {'count': 0, 'seconds': 0, 'night': 0, 'towers': set(), 'first': None, 'last': None})
    numbers, towers = (set(), {})
    for r in rows:
        a, b = (_norm_msisdn(r['caller_msisdn']), _norm_msisdn(r['callee_msisdn']))
        ts = datetime.strptime(r['timestamp'], '%Y-%m-%d %H:%M:%S')
        p = pairs[a, b]
        p['count'] += 1
        p['seconds'] += int(r['duration_sec'])
        if ts.hour >= 22 or ts.hour <= 5:
            p['night'] += 1
        p['towers'].add(r['tower_location'])
        p['first'] = min(p['first'] or ts, ts)
        p['last'] = max(p['last'] or ts, ts)
        numbers.update([a, b])
        towers[r['tower_location']] = r['tower_id']
    entities: List[Dict[str, Any]] = []
    index: Dict[str, str] = {}
    n = 0
    for num in sorted(numbers):
        n += 1
        eid = f'e{n}'
        entities.append(_mk(eid, 'PHONE', num, num))
        index[num] = eid
        owner = PHONE_OWNERS.get(num)
        if owner:
            n += 1
            oid = f'e{n}'
            ent = _mk(oid, 'PERSON', owner, owner, conf=0.95)
            ent['cluster_id'] = f's_PERSON_{owner}'
            entities.append(ent)
            index['owner:' + num] = oid
    for loc, tid in sorted(towers.items()):
        n += 1
        eid = f'e{n}'
        entities.append(_mk(eid, 'LOCATION', loc, loc, conf=0.9))
        index['loc:' + loc] = eid
    relationships: List[Dict[str, Any]] = []
    for num, eid in index.items():
        if num.startswith(('owner:', 'loc:')):
            continue
        oid = index.get('owner:' + num)
        if oid:
            relationships.append({'source': oid, 'target': eid, 'type': 'USES_PHONE', 'confidence': 0.95, 'evidence': f'Subscriber register: {num} registered to {PHONE_OWNERS[num]}.', 'attributes': {}})
    for (a, b), p in sorted(pairs.items()):
        src = index.get('owner:' + a) or index[a]
        tgt = index.get('owner:' + b) or index[b]
        conf = round(min(0.96, 0.62 + 0.05 * min(p['count'], 6)), 3)
        relationships.append({'source': src, 'target': tgt, 'type': 'CALLED', 'confidence': conf, 'evidence': f'{p['count']} calls between {a} and {b} totalling {p['seconds']}s, {p['first']:%d/%m/%Y} to {p['last']:%d/%m/%Y}.', 'attributes': {'call_count': p['count'], 'total_seconds': p['seconds'], 'night_calls': p['night'], 'towers': sorted(p['towers']), 'first_call': p['first'].isoformat(), 'last_call': p['last'].isoformat()}})
    return {'doc_id': doc_id, 'source_type': 'CDR', 'language': 'en', 'entities': entities, 'relationships': relationships, 'meta': {'pipeline_version': PIPELINE_VERSION, 'ner_model': 'n/a (structured)', 'ocr_used': False, 'record_count': len(rows), 'entity_count': len(entities), 'relationship_count': len(relationships), 'cluster_count': len({e['cluster_id'] for e in entities}), 'review_suggestions': [], 'warnings': []}}

def parse_transactions(path: pathlib.Path, doc_id: str='TXN-2026-Q1') -> Dict[str, Any]:
    with path.open(encoding='utf-8') as f:
        rows = list(csv.DictReader(f))
    entities: List[Dict[str, Any]] = []
    index: Dict[str, str] = {}
    n = 0

    def ensure(etype: str, value: str, conf: float=0.98) -> str:
        nonlocal n
        key = f'{etype}:{value}'
        if key in index:
            return index[key]
        n += 1
        eid = f'e{n}'
        ent = _mk(eid, etype, value, value, conf)
        ent['cluster_id'] = f's_{etype}_{value}'
        entities.append(ent)
        index[key] = eid
        return eid
    relationships: List[Dict[str, Any]] = []
    for r in rows:
        sender = ensure('PERSON', r['sender_name'], 0.96)
        acct = ensure('BANK_ACCOUNT', r['sender_account'])
        ensure('IFSC', r['ifsc'])
        rname = r['receiver_name']
        rtype = 'ORGANIZATION' if any((w in rname.lower() for w in ('ltd', 'pvt', 'logistics', 'exports', 'enterprises', 'traders'))) else 'PERSON'
        receiver = ensure(rtype, rname, 0.96)
        amount = float(r['amount_inr'])
        relationships.append({'source': sender, 'target': receiver, 'type': 'TRANSFERRED_TO', 'confidence': 0.97, 'evidence': f'{r['mode']} of Rs. {amount:,.0f} from {r['sender_name']} to {rname} on {r['date']}.', 'attributes': {'amount': f'{amount:.2f}', 'date': r['date'], 'mode': r['mode'], 'account': r['sender_account']}})
        relationships.append({'source': sender, 'target': acct, 'type': 'OWNS_ACCOUNT', 'confidence': 0.97, 'evidence': f'Account {r['sender_account']} operated by {r['sender_name']}.', 'attributes': {}})
    total = sum((float(r['amount_inr']) for r in rows))
    return {'doc_id': doc_id, 'source_type': 'TRANSACTION', 'language': 'en', 'entities': entities, 'relationships': relationships, 'meta': {'pipeline_version': PIPELINE_VERSION, 'ner_model': 'n/a (structured)', 'ocr_used': False, 'record_count': len(rows), 'total_value_inr': total, 'entity_count': len(entities), 'relationship_count': len(relationships), 'cluster_count': len({e['cluster_id'] for e in entities}), 'review_suggestions': [], 'warnings': []}}