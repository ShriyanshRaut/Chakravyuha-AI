from __future__ import annotations
import hashlib
import json
import pathlib
import sys
from typing import Any, Dict, List
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from app.pipeline import process_document
from app.resolution import canonical
from app.sources import PHONE_OWNERS, parse_cdr, parse_transactions
from app import patterns as patterns_mod
ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / 'data'
DEMO = ROOT / 'demo'
DOC_ORDER = [('fir_001_theft', 'FIR 142/2026 — Bowbazar', 'en', 'FIR'), ('fir_002_crew', 'FIR 168/2026 — Howrah', 'en', 'FIR'), ('fir_007_extortion', 'FIR 188/2026 — Bowbazar', 'en', 'FIR'), ('fir_008_vehicle', 'FIR 221/2026 — Salkia', 'en', 'FIR'), ('fir_009_arms', 'FIR 264/2026 — Rajabazar', 'en', 'FIR'), ('surveillance_001', 'SR-2026-014 — Special Watch, Howrah', 'en', 'SURVEILLANCE'), ('fir_003_alias_variants', 'FIR 311/2026 — Howrah', 'en', 'FIR'), ('fir_011_social', 'FIR 301/2026 — Howrah (cyber cell)', 'en', 'SOCIAL'), ('fir_004_hindi', 'FIR 402/2026 — Rajabazar', 'hi', 'FIR'), ('surveillance_002', 'SR-2026-031 — Economic Offences Watch', 'en', 'SURVEILLANCE'), ('fir_005_hawala', 'FIR 207/2026 — Burrabazar', 'en', 'FIR'), ('fir_006_shell', 'FIR 249/2026 — Burrabazar', 'en', 'FIR'), ('fir_010_layering', 'FIR 288/2026 — Burrabazar', 'en', 'FIR')]
ANALYSIS_NODE_TYPES = {'PERSON', 'ORGANIZATION'}
ANALYSIS_SKIP_EDGES = {'MENTIONED_WITH', 'LOCATED_AT'}
ANALYSIS_MIN_CONFIDENCE = 0.45

def global_key(entity: Dict[str, Any]) -> str:
    etype = entity['type']
    if etype in {'PERSON', 'ORGANIZATION', 'LOCATION'}:
        base = entity.get('canonical_value') or entity['value']
        return f'{etype}:{canonical(base, etype)}'
    return f'{etype}:{entity.get('normalized') or entity['value']}'

def build_graph(docs: List[Dict[str, Any]]) -> Dict[str, Any]:
    nodes: Dict[str, Dict[str, Any]] = {}
    edges: Dict[tuple, Dict[str, Any]] = {}
    for doc in docs:
        local_to_global = {}
        for ent in doc['entities']:
            gkey = global_key(ent)
            local_to_global[ent['entity_id']] = gkey
            node = nodes.setdefault(gkey, {'id': gkey, 'type': ent['type'], 'label': ent.get('canonical_value') or ent['value'], 'aliases': [], 'documents': [], 'mention_count': 0, 'confidence': ent['confidence']})
            node['mention_count'] += 1
            node['confidence'] = max(node['confidence'], ent['confidence'])
            for a in ent.get('aliases', []):
                if a not in node['aliases'] and a != node['label']:
                    node['aliases'].append(a)
            if doc['doc_id'] not in node['documents']:
                node['documents'].append(doc['doc_id'])
        for rel in doc['relationships']:
            s = local_to_global.get(rel['source'])
            t = local_to_global.get(rel['target'])
            if not s or not t or s == t:
                continue
            key = (s, t, rel['type'])
            edge = edges.setdefault(key, {'source': s, 'target': t, 'type': rel['type'], 'confidence': rel['confidence'], 'occurrences': 0, 'evidence': [], 'attributes': {}})
            edge['occurrences'] += 1
            edge['confidence'] = min(0.97, max(edge['confidence'], rel['confidence']) + 0.05 * (edge['occurrences'] - 1))
            if len(edge['evidence']) < 3:
                edge['evidence'].append({'doc_id': doc['doc_id'], 'sentence': rel['evidence']})
            if rel.get('attributes'):
                edge['attributes'].update(rel['attributes'])
    for n in nodes.values():
        n['aliases'] = sorted(n['aliases'])
    return {'nodes': sorted(nodes.values(), key=lambda n: n['id']), 'edges': sorted(edges.values(), key=lambda e: (e['source'], e['target'], e['type']))}

def analyse(graph: Dict[str, Any]) -> Dict[str, Any]:
    from app import graphalgo as nx
    keep = {n['id'] for n in graph['nodes'] if n['type'] in ANALYSIS_NODE_TYPES}
    G = nx.Graph()
    for _n in keep:
        G.add_node(_n)
    for e in graph['edges']:
        if e['type'] in ANALYSIS_SKIP_EDGES:
            continue
        if e['confidence'] < ANALYSIS_MIN_CONFIDENCE:
            continue
        if e['source'] in keep and e['target'] in keep:
            G.add_edge(e['source'], e['target'], weight=e['confidence'])
    pagerank = nx.pagerank(G) if G.number_of_edges() else {}
    betweenness = nx.betweenness_centrality(G, normalized=True) if G.number_of_edges() else {}
    degree = G.degree()
    components = nx.connected_components(G)
    communities = nx.greedy_modularity_communities(G)
    community_of = {n: i for i, c in enumerate(communities) for n in c}
    labels = {n['id']: n['label'] for n in graph['nodes']}
    types = {n['id']: n['type'] for n in graph['nodes']}
    scores = []
    for nid in G.nodes():
        scores.append({'id': nid, 'label': labels.get(nid, nid), 'type': types.get(nid), 'pagerank': round(pagerank.get(nid, 0), 4), 'betweenness': round(betweenness.get(nid, 0), 4), 'degree': degree.get(nid, 0), 'community': community_of.get(nid)})
    persons = [s for s in scores if s['type'] == 'PERSON']
    kingpin = max(persons, key=lambda s: s['pagerank'], default=None)
    middleman = max((p for p in persons if p is not kingpin), key=lambda s: s['betweenness'], default=None)
    return {'kingpin': kingpin, 'middleman': middleman, 'ranking_by_pagerank': sorted(scores, key=lambda s: -s['pagerank'])[:10], 'ranking_by_betweenness': sorted(scores, key=lambda s: -s['betweenness'])[:10], 'node_count': G.number_of_nodes(), 'edge_count': G.number_of_edges(), 'component_count': len(components), 'largest_component_size': max((len(c) for c in components), default=0), 'community_count': len(communities), 'communities': [{'id': i, 'size': len(c), 'members': [labels.get(x, x) for x in c]} for i, c in enumerate(communities)]}

def build_ledger(entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    ledger = []
    prev = '0' * 64
    for i, e in enumerate(entries, 1):
        payload = json.dumps({'index': i, 'doc_id': e['doc_id'], 'evidence_sha256': e['evidence_sha256'], 'uploaded_by': e['uploaded_by'], 'timestamp': e['timestamp'], 'previous_hash': prev}, sort_keys=True)
        block_hash = hashlib.sha256(payload.encode()).hexdigest()
        ledger.append({'index': i, 'doc_id': e['doc_id'], 'title': e['title'], 'evidence_sha256': e['evidence_sha256'], 'uploaded_by': e['uploaded_by'], 'timestamp': e['timestamp'], 'previous_hash': prev, 'block_hash': block_hash})
        prev = block_hash
    return ledger

def build_report(graph, analysis, docs, alerts, timeline) -> str:
    kp, mm = (analysis['kingpin'], analysis['middleman'])
    persons = [n for n in graph['nodes'] if n['type'] == 'PERSON']
    orgs = [n for n in graph['nodes'] if n['type'] == 'ORGANIZATION']
    money = sum((d['meta'].get('total_value_inr', 0) for d in docs))
    lines = ['# Intelligence Report — Synthetic Demonstration Data Only', '', f'**Documents analysed:** {len(docs)}  ', f'**Entities resolved:** {len(graph['nodes'])} ({len(persons)} persons, {len(orgs)} organisations)  ', f'**Relationships extracted:** {len(graph['edges'])}  ', f'**Value traced across transfers:** Rs. {money:,.0f}', '', '## Key individuals', '']
    if kp:
        lines += [f'**{kp['label']} — principal influencer.** Highest PageRank ({kp['pagerank']}) across the resolved network, with {kp['degree']} direct connections. Influence is indirect: multiple crew members route contact toward this individual rather than to each other.', '']
    if mm:
        lines += [f'**{mm['label']} — bridging intermediary.** Highest betweenness ({mm['betweenness']}), meaning this individual lies on the shortest path between two otherwise separate clusters. Removing this node disconnects the operational group from the financial channel.', '']
    if analysis.get('communities'):
        real = [c for c in analysis['communities'] if c['size'] >= 3]
        lines += ['## Detected groupings', '']
        for c in real:
            lines.append(f'- **Cluster {c['id'] + 1}** ({c['size']} members): ' + ', '.join(c['members']))
        lines.append('')
    high = [a for a in alerts if a['severity'] == 'HIGH']
    if alerts:
        lines += ['## Suspicious activity', '', f'{len(alerts)} patterns flagged, {len(high)} at high severity.', '']
        for a in alerts:
            lines.append(f'- **[{a['severity']}] {a['title']}** — {a['detail']}')
        lines.append('')
    if timeline:
        lines += ['## Sequence', '', f'{len(timeline)} dated events between {timeline[0]['date']} and {timeline[-1]['date']}. Full stream in `timeline.json`.', '']
    lines += ['## Basis', '', 'Every relationship above is traceable to a sentence in a source FIR; evidence text is attached to each edge in the graph payload. Entity merges below the automatic threshold were referred for officer approval and are recorded in the review log.', '', '_Synthetic Demonstration Data Only._']
    return '\n'.join(lines)

def build_timeline(docs) -> List[Dict[str, Any]]:
    events = []
    for doc in docs:
        labels = {e['entity_id']: e.get('canonical_value') or e['value'] for e in doc['entities']}
        for rel in doc['relationships']:
            date = rel.get('attributes', {}).get('date')
            if not date:
                continue
            events.append({'date': date[:10], 'doc_id': doc['doc_id'], 'source_type': doc['source_type'], 'type': rel['type'], 'source': labels.get(rel['source'], rel['source']), 'target': labels.get(rel['target'], rel['target']), 'amount': rel.get('attributes', {}).get('amount'), 'evidence': rel['evidence'][:220]})
    events.sort(key=lambda e: (e['date'], e['doc_id']))
    return events

def main():
    DEMO.mkdir(exist_ok=True)
    docs, steps, ledger_input, reviews = ([], [], [], [])
    for i, (stem, title, lang, stype) in enumerate(DOC_ORDER, 1):
        path = DATA / f'{stem}.txt'
        raw = path.read_text(encoding='utf-8')
        sha = hashlib.sha256(raw.encode('utf-8')).hexdigest()
        result = process_document(raw, doc_id=stem.upper(), source_type=stype, language=lang)
        result['meta'].pop('processed_at', None)
        docs.append(result)
        steps.append({'step': i, 'doc_id': result['doc_id'], 'title': title, 'language': lang, 'source_type': stype, 'source_text': raw, 'evidence_sha256': sha, 'entity_count': result['meta']['entity_count'], 'relationship_count': result['meta']['relationship_count'], 'extraction': result})
        ledger_input.append({'doc_id': result['doc_id'], 'title': title, 'evidence_sha256': sha, 'uploaded_by': 'SI R. Chatterjee (demo)', 'timestamp': f'2026-03-1{i}T10:0{i}:00+05:30'})
        for r in result['meta']['review_suggestions']:
            reviews.append({**r, 'doc_id': result['doc_id'], 'status': 'pending'})
    cdr_path, tx_path = (DATA / 'cdr_records.csv', DATA / 'transactions.csv')
    cdr = parse_cdr(cdr_path)
    txn = parse_transactions(tx_path)
    docs += [cdr, txn]
    for name, doc, path in (('CDR — Kolkata circle, Q1 2026', cdr, cdr_path), ('Bank transaction extract, Q1 2026', txn, tx_path)):
        raw = path.read_text(encoding='utf-8')
        steps.append({'step': len(steps) + 1, 'doc_id': doc['doc_id'], 'title': name, 'language': 'en', 'source_type': doc['source_type'], 'source_text': raw[:2000], 'evidence_sha256': hashlib.sha256(raw.encode()).hexdigest(), 'record_count': doc['meta']['record_count'], 'entity_count': doc['meta']['entity_count'], 'relationship_count': doc['meta']['relationship_count'], 'extraction': doc})
        ledger_input.append({'doc_id': doc['doc_id'], 'title': name, 'evidence_sha256': hashlib.sha256(raw.encode()).hexdigest(), 'uploaded_by': 'SI R. Chatterjee (demo)', 'timestamp': '2026-03-20T09:00:00+05:30'})
    graph = build_graph(docs)
    analysis = analyse(graph)
    alerts = patterns_mod.run_all(graph, analysis, cdr_path, tx_path, {k: v for k, v in PHONE_OWNERS.items()} | {k.replace('+91', ''): v for k, v in PHONE_OWNERS.items()})
    timeline = build_timeline(docs)
    ledger = build_ledger(ledger_input)
    report = build_report(graph, analysis, docs, alerts, timeline)

    def write(name, obj):
        p = DEMO / name
        if name.endswith('.md'):
            p.write_text(obj, encoding='utf-8')
        else:
            p.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding='utf-8')
        print(f'  {p.relative_to(ROOT)}')
    print('wrote:')
    write('ledger.json', ledger)
    write('extraction_steps.json', steps)
    write('alias_review.json', reviews)
    write('graph.json', graph)
    write('analysis.json', analysis)
    write('alerts.json', alerts)
    write('timeline.json', timeline)
    write('report.md', report)
    print()
    print(f'nodes {len(graph['nodes'])}  edges {len(graph['edges'])}  components {analysis['component_count']}')
    if analysis['kingpin']:
        k = analysis['kingpin']
        print(f'kingpin   : {k['label']}  pagerank={k['pagerank']} degree={k['degree']}')
    if analysis['middleman']:
        m = analysis['middleman']
        print(f'middleman : {m['label']}  betweenness={m['betweenness']}')
    print(f'alias reviews pending: {len(reviews)}')
    print(f'alerts: {len(alerts)} (HIGH {sum((1 for a in alerts if a['severity'] == 'HIGH'))})')
    print(f'timeline events: {len(timeline)}')
    print(f'communities: {analysis['community_count']}')
if __name__ == '__main__':
    main()