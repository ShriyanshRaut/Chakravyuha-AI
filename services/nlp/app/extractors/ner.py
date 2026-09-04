from __future__ import annotations
import re
from typing import Any, Dict, List
from app.extractors.gazetteer import DEMO_ORGS, GANG_NAMES, INDIAN_GIVEN_NAMES, INDIAN_SURNAMES, LOCATIONS, POLICE_STATIONS, WEAPONS
ABBREVIATIONS = {'rs', 'no', 'nos', 'pvt', 'ltd', 'co', 'sri', 'shri', 'smt', 'md', 'mohd', 'mr', 'mrs', 'ms', 'dr', 'hrs', 'sec', 'vs', 'approx', 'fir', 'ipc'}
CONF_RULER = 0.93
GIVEN = {n.lower() for n in INDIAN_GIVEN_NAMES}
SURNAMES = {s.lower() for s in INDIAN_SURNAMES}
HONORIFICS = {'sri', 'shri', 'smt', 'md', 'mohd', 'mr', 'mrs', 'ms', 'dr'}
PHRASES: List[tuple] = []
for _p in sorted(POLICE_STATIONS, key=len, reverse=True):
    PHRASES.append((_p, 'LOCATION'))
for _p in sorted(GANG_NAMES + DEMO_ORGS, key=len, reverse=True):
    PHRASES.append((_p, 'ORGANIZATION'))
for _p in sorted(WEAPONS, key=len, reverse=True):
    PHRASES.append((_p, 'WEAPON'))
for _p in sorted(LOCATIONS, key=len, reverse=True):
    PHRASES.append((_p, 'LOCATION'))
TOKEN = re.compile(r"[A-Za-z][A-Za-z.'\-]*")

def model_name() -> str:
    return 'gazetteer'

def _phrase_matches(text: str) -> List[Dict[str, Any]]:
    out = []
    for phrase, etype in PHRASES:
        for m in re.finditer(r'\b' + re.escape(phrase) + r'\b', text, re.IGNORECASE):
            out.append({'type': etype, 'value': text[m.start():m.end()], 'normalized': phrase, 'confidence': CONF_RULER, 'extractor': 'ner', 'spans': [{'start': m.start(), 'end': m.end()}]})
    return out

def _person_matches(text: str) -> List[Dict[str, Any]]:
    toks = [(m.group(0), m.start(), m.end()) for m in TOKEN.finditer(text)]
    out, i = ([], 0)
    while i < len(toks):
        word, start, end = toks[i]
        low = word.lower().rstrip('.')
        parts = None
        if low in HONORIFICS and i + 2 < len(toks) and toks[i + 1][0][:1].isupper() and toks[i + 2][0][:1].isupper():
            parts = toks[i:i + 3]
        elif low in GIVEN and i + 2 < len(toks) and (toks[i + 1][0][:1].isupper() and toks[i + 2][0].lower() in SURNAMES):
            parts = toks[i:i + 3]
        elif low in GIVEN and i + 1 < len(toks) and toks[i + 1][0][:1].isupper():
            parts = toks[i:i + 2]
        elif re.fullmatch(r"[A-Z]\.?", word) and i + 1 < len(toks) and (toks[i + 1][0].lower() in SURNAMES):
            parts = toks[i:i + 2]
        if parts:
            s, e = (parts[0][1], parts[-1][2])
            while e > s and text[e - 1] in '.-\'' and (not re.fullmatch(r'[A-Z]\.', text[e - 2:e])):
                e -= 1
            out.append({'type': 'PERSON', 'value': text[s:e], 'normalized': text[s:e], 'confidence': CONF_RULER, 'extractor': 'ner', 'spans': [{'start': s, 'end': e}]})
            i += len(parts)
        else:
            i += 1
    return out

def _overlap(a, b) -> bool:
    return a['spans'][0]['start'] < b['spans'][0]['end'] and b['spans'][0]['start'] < a['spans'][0]['end']

def extract_ner_entities(text: str) -> List[Dict[str, Any]]:
    persons = _person_matches(text)
    kept = list(persons)
    for cand in _phrase_matches(text):
        if not any((_overlap(cand, k) for k in kept)):
            kept.append(cand)
    kept.sort(key=lambda e: e['spans'][0]['start'])
    return kept

def sentences(text: str) -> List[Dict[str, Any]]:
    spans, start = ([], 0)
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        if ch in '।॥':
            spans.append({'text': text[start:i + 1], 'start': start, 'end': i + 1})
            i += 1
            while i < n and text[i].isspace():
                i += 1
            start = i
            continue
        if ch in '.!?':
            prev = re.search(r"([A-Za-z/]+)$", text[:i])
            abbrev = bool(prev) and prev.group(1).lower() in ABBREVIATIONS
            nxt = text[i + 1:i + 2]
            if not abbrev and (nxt == '' or nxt.isspace()):
                spans.append({'text': text[start:i + 1], 'start': start, 'end': i + 1})
                i += 1
                while i < n and text[i].isspace():
                    i += 1
                start = i
                continue
        i += 1
    if start < n:
        spans.append({'text': text[start:], 'start': start, 'end': n})
    return [s for s in spans if s['text'].strip()]