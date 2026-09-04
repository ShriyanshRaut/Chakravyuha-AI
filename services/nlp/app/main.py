from __future__ import annotations
from typing import List
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from app.extractors.ner import model_name
from app.pipeline import PIPELINE_VERSION, process_document
app = FastAPI(title='Chakravyuha AI — NLP Extraction Service', description='FIR text in, graph-ready entities and relationships out.', version=PIPELINE_VERSION)
app.add_middleware(CORSMiddleware, allow_origins=['*'], allow_methods=['*'], allow_headers=['*'])

class ExtractRequest(BaseModel):
    text: str = Field(..., min_length=1, description='Raw FIR / report text')
    doc_id: str = Field('DOC-UNKNOWN', description='Stable id, e.g. FIR-2026-0142')
    source_type: str = Field('FIR', description='FIR | CDR | TRANSACTION | SURVEILLANCE | SOCIAL | OTHER')
    language: str = Field('en', description='BCP-47 tag')

@app.get('/health')
def health():
    return {'status': 'ok', 'pipeline_version': PIPELINE_VERSION, 'ner_model': model_name()}

@app.post('/extract')
def extract(req: ExtractRequest):
    try:
        return process_document(req.text, doc_id=req.doc_id, source_type=req.source_type, language=req.language)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f'extraction failed: {exc}')

@app.post('/extract/batch')
def extract_batch(reqs: List[ExtractRequest]):
    if len(reqs) > 50:
        raise HTTPException(status_code=413, detail='max 50 documents per batch')
    return [process_document(r.text, doc_id=r.doc_id, source_type=r.source_type, language=r.language) for r in reqs]

@app.post('/extract/file')
async def extract_file(file: UploadFile=File(...)):
    raw = await file.read()
    try:
        text = raw.decode('utf-8')
    except UnicodeDecodeError:
        text = raw.decode('latin-1')
    return process_document(text, doc_id=(file.filename or 'UPLOAD').rsplit('.', 1)[0].upper())