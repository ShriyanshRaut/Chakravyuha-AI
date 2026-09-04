import os
from dotenv import load_dotenv

# Load environment variables from the .env file
load_dotenv()

class Settings:
    PROJECT_NAME: str = "Chakravyuha AI"
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5432/chakravyuha")
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "default-secret")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

settings = Settings()