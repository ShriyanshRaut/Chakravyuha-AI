from __future__ import annotations
import re
import unicodedata
from datetime import datetime, timezone
from typing import Any, Dict, List
from app.extractors.regex_extractors import extract_regex_entities
from app.extractors.ner import extract_ner_entities, model_name
from app.relations import extract_relationships
from app.resolution import alias_marker_reviews, resolve_entities
PIPELINE_VERSION = '0.2.0'

def clean_text(text: str) -> str:
    text = unicodedata.normalize('NFKC', text)
    text = text.replace('\r\n', '\n').replace('\u200b', '')
    text = re.sub('[ \\t]+', ' ', text)
    return text.strip()

def _overlaps(a: Dict, b: Dict) -> bool:
    s1, e1 = (a['spans'][0]['start'], a['spans'][0]['end'])
    s2, e2 = (b['spans'][0]['start'], b['spans'][0]['end'])
    return s1 < e2 and s2 < e1

def dedupe(regex_ents: List[Dict], ner_ents: List[Dict]) -> List[Dict]:
    kept = list(regex_ents)
    for n in ner_ents:
        if not any((_overlaps(n, r) for r in regex_ents)):
            kept.append(n)
    kept.sort(key=lambda e: e['spans'][0]['start'])
    return kept

def process_document(text: str, doc_id: str, source_type: str='FIR', language: str='en', ocr_used: bool=False) -> Dict[str, Any]:
    warnings: List[str] = []
    cleaned = clean_text(text)
    if not cleaned:
        warnings.append('empty document after cleaning')
    regex_ents = extract_regex_entities(cleaned)
    ner_ents = extract_ner_entities(cleaned)
    mdl = model_name()
    if mdl == 'unavailable':
        warnings.append('spaCy not installed — PERSON/ORG/LOCATION not extracted')
    elif mdl == 'blank':
        warnings.append('no spaCy model found — gazetteer only, run: python -m spacy download en_core_web_trf')
    elif mdl == 'en_core_web_sm':
        warnings.append('using en_core_web_sm — accuracy is lower than en_core_web_trf')
    entities = dedupe(regex_ents, ner_ents)
    for i, e in enumerate(entities, 1):
        e['entity_id'] = f'e{i}'
    entities, reviews = resolve_entities(entities)
    reviews += alias_marker_reviews(entities)
    relationships = extract_relationships(cleaned, entities)
    return {'doc_id': doc_id, 'source_type': source_type, 'language': language, 'text_length': len(cleaned), 'entities': entities, 'relationships': relationships, 'meta': {'pipeline_version': PIPELINE_VERSION, 'ner_model': mdl, 'processed_at': datetime.now(timezone.utc).isoformat(), 'ocr_used': ocr_used, 'entity_count': len(entities), 'cluster_count': len({e.get('cluster_id') for e in entities}), 'relationship_count': len(relationships), 'review_suggestions': reviews, 'warnings': warnings}}
if __name__ == '__main__':
    import json
    import pathlib
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else 'data/fir_001_theft.txt'
    raw = pathlib.Path(path).read_text(encoding='utf-8')
    doc_id = pathlib.Path(path).stem.upper()
    print(json.dumps(process_document(raw, doc_id=doc_id), indent=2, ensure_ascii=False))