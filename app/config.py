from pydantic import BaseModel
from pathlib import Path
import os

class Settings(BaseModel):
    DATABASE_URL: str
    PRIVATE_KEY_PATH: str
    PUBLIC_KEY_PATH: str
    JWT_ALGO: str = "RS512"
    JWT_EXPIRE_MINUTES: int = 60 * 24 * 7

    @property
    def private_key(self) -> str:
        return Path(self.PRIVATE_KEY_PATH).read_text()

    @property
    def public_key(self) -> str:
        return Path(self.PUBLIC_KEY_PATH).read_text()

# Manual loading from .env
from dotenv import load_dotenv
load_dotenv()


settings = Settings(
    DATABASE_URL=os.getenv("DATABASE_URL"),
    PRIVATE_KEY_PATH = os.getenv("JWT_PRIVATE_KEY_PATH"),
    PUBLIC_KEY_PATH = os.getenv("JWT_PUBLIC_KEY_PATH"),
    JWT_ALGO = os.getenv("JWT_ALGORITHM", "RS512"),
    JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", 60 * 24 * 7))
)
