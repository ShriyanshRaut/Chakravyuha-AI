from __future__ import annotations
import re
from typing import Any, Dict, List, Tuple
MERGE_THRESHOLD = 88
REVIEW_THRESHOLD = 72
FUZZY_TYPES = {'PERSON', 'ORGANIZATION', 'LOCATION'}
HONORIFICS = re.compile('^(?:shri|sri|smt|smt\\.|mr|mrs|ms|dr|md|mohd|maulana|haji)\\.?\\s+', re.I)
ORG_SUFFIXES = re.compile('\\b(?:pvt|private|ltd|limited|llp|inc|co|company|corp|enterprises|traders|gang|group)\\b\\.?', re.I)

def canonical(value: str, etype: str) -> str:
    v = value.strip()
    if etype == 'PERSON':
        v = HONORIFICS.sub('', v)
    if etype == 'ORGANIZATION':
        v = ORG_SUFFIXES.sub('', v)
    v = re.sub('[^\\w\\s]', ' ', v.lower())
    return re.sub('\\s+', ' ', v).strip()

def _initials_match(a: str, b: str) -> bool:
    ta, tb = (a.split(), b.split())
    if len(ta) < 2 or len(tb) < 2 or ta[-1] != tb[-1]:
        return False
    fa, fb = (ta[0], tb[0])
    return len(fa) == 1 and fb.startswith(fa) or (len(fb) == 1 and fa.startswith(fb))

def score_pair(a: str, b: str) -> int:
    if a == b:
        return 100
    if _initials_match(a, b):
        return 92
    try:
        from rapidfuzz import fuzz
    except ImportError:
        return 0
    return int(max(fuzz.token_sort_ratio(a, b), fuzz.token_set_ratio(a, b)))

def resolve_entities(entities: List[Dict[str, Any]]) -> Tuple[List[Dict], List[Dict]]:
    clusters: List[Dict[str, Any]] = []
    reviews: List[Dict[str, Any]] = []
    for ent in entities:
        etype = ent['type']
        key = canonical(ent['value'], etype) if etype in FUZZY_TYPES else str(ent.get('normalized') or ent['value'])
        placed = False
        for c in clusters:
            if c['type'] != etype:
                continue
            if etype in FUZZY_TYPES:
                score = score_pair(c['key'], key)
            else:
                score = 100 if c['key'] == key else 0
            if score >= MERGE_THRESHOLD:
                c['members'].append(ent)
                placed = True
                break
            if REVIEW_THRESHOLD <= score < MERGE_THRESHOLD:
                reviews.append({'type': etype, 'candidate_a': c['members'][0]['value'], 'candidate_b': ent['value'], 'score': score, 'action': 'possible_same_entity_needs_human_review'})
        if not placed:
            clusters.append({'key': key, 'type': etype, 'members': [ent]})
    for i, c in enumerate(clusters, 1):
        cid = f'c{i}'
        forms = {m['value'] for m in c['members']}
        canonical_form = max(sorted(forms), key=len)
        for m in c['members']:
            m['cluster_id'] = cid
            m['aliases'] = sorted(forms - {m['value']})
            m['canonical_value'] = canonical_form
    seen, unique = (set(), [])
    for r in reviews:
        k = tuple(sorted([r['candidate_a'], r['candidate_b']]))
        if k not in seen:
            seen.add(k)
            unique.append(r)
    return (entities, unique)

def alias_marker_reviews(entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    reviews = []
    persons = [e for e in entities if e['type'] == 'PERSON']
    for ent in persons:
        if not ent.get('alias_marked'):
            continue
        start = ent['spans'][0]['start']
        prior = [p for p in persons if not p.get('alias_marked') and p['spans'][0]['end'] <= start]
        if not prior:
            continue
        anchor = max(prior, key=lambda p: p['spans'][0]['end'])
        if anchor.get('cluster_id') == ent.get('cluster_id'):
            continue
        reviews.append({'type': 'PERSON', 'candidate_a': anchor.get('canonical_value') or anchor['value'], 'candidate_b': ent['value'], 'score': score_pair(canonical(anchor['value'], 'PERSON'), canonical(ent['value'], 'PERSON')), 'reason': "document states 'alias' but the names do not match", 'action': 'possible_same_entity_needs_human_review'})
    return reviews