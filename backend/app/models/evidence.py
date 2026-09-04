from sqlalchemy import Column, String, DateTime
from datetime import datetime, timezone
import uuid
from app.db.session import Base

class Evidence(Base):
    __tablename__ = "evidence"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    case_id = Column(String, nullable=True, index=True)
    original_filename = Column(String, nullable=False)
    saved_filename = Column(String, nullable=False)
    sha256_hash = Column(String(64), nullable=False)
    tamper_status = Column(String, default="Verified - Initial Upload")
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))