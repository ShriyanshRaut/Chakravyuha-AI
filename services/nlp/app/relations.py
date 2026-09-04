from __future__ import annotations
import re
from typing import Any, Dict, List, Optional
from app.extractors.ner import sentences
TRIGGERS = [('\\b(?:called|phoned|dialled|dialed|rang|contacted|spoke (?:to|with)|in touch with|conversation with)\\b', 'CALLED', 0.86), ('\\b(?:transferred|remitted|paid|sent|credited|deposited|wired|hawala|routed (?:through|via))\\b', 'TRANSFERRED_TO', 0.85), ('\\b(?:owns|owner of|registered (?:to|in the name of|under)|driving|drove|fled in|escaped in|absconded in|vehicle bearing)\\b', 'OWNS_VEHICLE', 0.82), ('\\b(?:using (?:mobile|phone|number|no\\.?)|from (?:mobile|number)|mobile no\\.?|contact no\\.?|whose number|registered mobile)\\b', 'USES_PHONE', 0.84), ('\\b(?:member of|belongs to|part of|associated with|working for|operative of|affiliated (?:to|with)|linked to)\\b', 'MEMBER_OF', 0.82), ('\\b(?:employed (?:by|at)|works (?:for|at)|proprietor of|director of|partner in)\\b', 'EMPLOYED_BY', 0.83), ('\\b(?:met|seen with|spotted with|accompanied by|along with|together with|in the company of|and his associate)\\b', 'SEEN_WITH', 0.79), ('\\b(?:brother|sister|father|mother|son|daughter|wife|husband|cousin|uncle|nephew|relative) of\\b', 'RELATED_TO', 0.88), ('(?:फोन किया|कॉल किया|संपर्क किया|बात की)', 'CALLED', 0.86), ('(?:भेजी|भेजा|स्थानांतरित|जमा किया|ट्रांसफर)', 'TRANSFERRED_TO', 0.85), ('(?:का सदस्य|से जुड़ा|गिरोह का)', 'MEMBER_OF', 0.82), ('(?:के साथ देखा|के साथ था|साथ में)', 'SEEN_WITH', 0.79), ('(?:के पास देखा|में पाया|से बरामद|निवासी)', 'LOCATED_AT', 0.75), ('(?:के नाम पर|का वाहन|चला रहा)', 'OWNS_VEHICLE', 0.82), ('\\b(?:residing at|resident of|hideout (?:at|in)|hiding (?:at|in)|operating from|based (?:at|in)|premises at|recovered from)\\b', 'LOCATED_AT', 0.75)]
VALID_PAIRS: Dict[str, set] = {'CALLED': {('PERSON', 'PERSON'), ('PERSON', 'PHONE'), ('PHONE', 'PHONE')}, 'TRANSFERRED_TO': {('PERSON', 'PERSON'), ('PERSON', 'BANK_ACCOUNT'), ('PERSON', 'ORGANIZATION'), ('BANK_ACCOUNT', 'BANK_ACCOUNT'), ('ORGANIZATION', 'ORGANIZATION'), ('BANK_ACCOUNT', 'ORGANIZATION')}, 'OWNS_VEHICLE': {('PERSON', 'VEHICLE'), ('ORGANIZATION', 'VEHICLE')}, 'USES_PHONE': {('PERSON', 'PHONE')}, 'MEMBER_OF': {('PERSON', 'ORGANIZATION')}, 'EMPLOYED_BY': {('PERSON', 'ORGANIZATION')}, 'SEEN_WITH': {('PERSON', 'PERSON')}, 'RELATED_TO': {('PERSON', 'PERSON')}, 'LOCATED_AT': {('PERSON', 'LOCATION'), ('ORGANIZATION', 'LOCATION'), ('VEHICLE', 'LOCATION'), ('PERSON', 'ORGANIZATION')}}
COOCCUR_PAIRS = {('PERSON', 'PERSON'), ('PERSON', 'ORGANIZATION'), ('PERSON', 'LOCATION'), ('ORGANIZATION', 'LOCATION')}
COOCCUR_CONF = 0.4
DISTANCE_LIMITED = {'LOCATED_AT': 90, 'MENTIONED_WITH': 90, 'SEEN_WITH': 120}

def _gap(a: Dict, b: Dict) -> int:
    return max(0, max(a['spans'][0]['start'], b['spans'][0]['start']) - min(a['spans'][0]['end'], b['spans'][0]['end']))

def _entities_in(sent: Dict, entities: List[Dict]) -> List[Dict]:
    return [e for e in entities if e['spans'][0]['start'] >= sent['start'] and e['spans'][0]['end'] <= sent['end']]

def _sentence_attributes(sent_ents: List[Dict]) -> Dict[str, Any]:
    attrs: Dict[str, Any] = {}
    for e in sent_ents:
        if e['type'] == 'MONEY' and 'amount' not in attrs:
            attrs['amount'] = e.get('normalized')
        if e['type'] == 'DATE' and 'date' not in attrs:
            attrs['date'] = e.get('normalized')
    return attrs

def _pick_relation(a: Dict, b: Dict, matched: List) -> Optional[tuple]:
    pair = (a['type'], b['type'])
    for rtype, conf in matched:
        valid = VALID_PAIRS.get(rtype, set())
        if pair in valid:
            return (a, b, rtype, conf)
        if (pair[1], pair[0]) in valid:
            return (b, a, rtype, conf)
    if pair in COOCCUR_PAIRS or (pair[1], pair[0]) in COOCCUR_PAIRS:
        return (a, b, 'MENTIONED_WITH', COOCCUR_CONF)
    return None

def extract_relationships(text: str, entities: List[Dict]) -> List[Dict[str, Any]]:
    rels: List[Dict[str, Any]] = []
    seen = set()
    for sent in sentences(text):
        in_sent = _entities_in(sent, entities)
        if len(in_sent) < 2:
            continue
        matched = [(rtype, conf) for pat, rtype, conf in TRIGGERS if re.search(pat, sent['text'], re.I)]
        attrs = _sentence_attributes(in_sent)
        for i, a in enumerate(in_sent):
            for b in in_sent[i + 1:]:
                if a.get('cluster_id') and a.get('cluster_id') == b.get('cluster_id'):
                    continue
                edge = _pick_relation(a, b, matched)
                if edge is None:
                    continue
                src, tgt, rtype, base = edge
                gap = _gap(a, b)
                limit = DISTANCE_LIMITED.get(rtype)
                if limit is not None and gap > limit:
                    continue
                base *= max(0.6, 1.0 - gap / 400)
                key = (src.get('cluster_id'), tgt.get('cluster_id'), rtype)
                if key in seen:
                    continue
                seen.add(key)
                conf = round(base * min(src['confidence'], tgt['confidence']), 3)
                rels.append({'source': src['entity_id'], 'target': tgt['entity_id'], 'source_cluster': src.get('cluster_id'), 'target_cluster': tgt.get('cluster_id'), 'type': rtype, 'confidence': conf, 'evidence': ' '.join(sent['text'].split()), 'evidence_span': {'start': sent['start'], 'end': sent['end']}, 'attributes': attrs if rtype == 'TRANSFERRED_TO' else {}})
    return rels