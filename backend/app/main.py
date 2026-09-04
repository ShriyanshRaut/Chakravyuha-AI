from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import evidence 

from app.db.session import engine, Base
from app.models.evidence import Evidence  
Base.metadata.create_all(bind=engine)     

app = FastAPI(
    title="Chakravyuha AI API",
    description="Secure Graph Intelligence Platform for Criminal Network Investigation",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Connect your new upload route!
app.include_router(evidence.router, prefix="/api/evidence", tags=["Evidence & Ledger"]) # <-- ADD THIS

@app.get("/health", tags=["System"])
async def health_check():
    return {"status": "online", "system": "Chakravyuha AI Core"}

@app.get("/cases", tags=["Investigation"])
async def get_mock_cases():
    return {
        "cases": [
            {"id": "CASE-001", "title": "Operation Red Phantom", "status": "Open"},
            {"id": "CASE-002", "title": "Syndicate Alpha", "status": "Under Review"}
        ]
    }