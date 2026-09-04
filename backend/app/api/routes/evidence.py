from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from sqlalchemy.orm import Session
from app.services.evidence_hashing import calculate_sha256
from app.db.session import get_db
from app.models.evidence import Evidence
import os
import uuid

router = APIRouter()

# Securely store uploads outside the web root
UPLOAD_DIR = "uploaded_evidence_secure"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/upload")
async def upload_evidence(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)  # <-- This injects our PostgreSQL connection!
):
    try:
        # 1. Read and hash the file
        file_bytes = await file.read()
        file_hash = calculate_sha256(file_bytes)
        
        # 2. Save securely off-chain
        safe_filename = f"{uuid.uuid4()}_{file.filename}"
        file_path = os.path.join(UPLOAD_DIR, safe_filename)
        
        with open(file_path, "wb") as f:
            f.write(file_bytes)
            
        # 3. Save the hash and metadata to the PostgreSQL database
        new_evidence = Evidence(
            original_filename=file.filename,
            saved_filename=safe_filename,
            sha256_hash=file_hash,
            tamper_status="Verified - Initial Upload"
        )
        
        db.add(new_evidence)
        db.commit()              # Saves to DB
        db.refresh(new_evidence) # Gets the auto-generated ID
        
        # 4. Return success response
        return {
            "message": "Evidence uploaded securely and logged to database",
            "evidence_id": new_evidence.id,
            "original_filename": new_evidence.original_filename,
            "sha256_hash": new_evidence.sha256_hash,
            "tamper_status": new_evidence.tamper_status
        }
    except Exception as e:
        print(f"Upload error: {e}") # Helpful for debugging in the terminal
        raise HTTPException(status_code=500, detail="Could not process file upload.")