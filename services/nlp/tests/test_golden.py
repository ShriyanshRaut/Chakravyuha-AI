import json
import pathlib
import sys
import pytest
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from app.pipeline import process_document
DATA = pathlib.Path(__file__).resolve().parents[1] / 'data'
FIXTURES = pathlib.Path(__file__).resolve().parents[3] / 'contracts' / 'fixtures'
GOLDEN_DOCS = ['fir_001_theft', 'fir_003_alias_variants', 'fir_005_hawala']

def run(stem: str) -> dict:
    text = (DATA / f'{stem}.txt').read_text(encoding='utf-8')
    out = process_document(text, doc_id=stem.upper())
    out['meta'].pop('processed_at', None)
    out['meta'].pop('ner_model', None)
    out['meta'].pop('warnings', None)
    return out

@pytest.mark.parametrize('stem', GOLDEN_DOCS)
def test_matches_golden(stem):
    expected_path = FIXTURES / f'{stem}.expected.json'
    if not expected_path.exists():
        pytest.skip(f'no fixture yet: run with --update')
    expected = json.loads(expected_path.read_text(encoding='utf-8'))
    assert run(stem) == expected

@pytest.mark.parametrize('stem', GOLDEN_DOCS)
def test_sane_output(stem):
    out = run(stem)
    assert out['entities'], 'no entities extracted'
    ids = {e['entity_id'] for e in out['entities']}
    for r in out['relationships']:
        assert r['source'] in ids and r['target'] in ids, 'dangling relationship'
        assert 0 <= r['confidence'] <= 1
    for e in out['entities']:
        assert e['cluster_id'], 'entity missing cluster_id'
if __name__ == '__main__':
    if '--update' in sys.argv:
        FIXTURES.mkdir(parents=True, exist_ok=True)
        for stem in GOLDEN_DOCS:
            p = FIXTURES / f'{stem}.expected.json'
            p.write_text(json.dumps(run(stem), indent=2, ensure_ascii=False), encoding='utf-8')
            print('wrote', p)